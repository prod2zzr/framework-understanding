"""CLI entry point for contract review."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from contract_reviewer.chunking.contract_parser import ContractParser
from contract_reviewer.chunking.splitter import ContractSplitter
from contract_reviewer.llm.client import LLMClient
from contract_reviewer.models.config import Settings
from contract_reviewer.models.progress import ProgressEvent
from contract_reviewer.ocr.factory import create_ocr_engine
from contract_reviewer.rag.embedder import Embedder
from contract_reviewer.rag.ingestor import KnowledgeIngestor
from contract_reviewer.rag.precomputed_queries import PrecomputedQueries
from contract_reviewer.rag.prompt_builder import PromptBuilder
from contract_reviewer.rag.retriever import Retriever
from contract_reviewer.rag.vectorstore import VectorStore
from contract_reviewer.review.aggregator import format_report_markdown
from contract_reviewer.review.batch import batch_review
from contract_reviewer.plugins.registry import discover_plugins
from contract_reviewer.review.engine import ReviewEngine
from contract_reviewer.review import rule_history

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="contract-review",
    help="AI 合同审核工具 — 支持云端/本地模型",
)
console = Console()


def _load_rules(rules_path: str) -> list[dict]:
    """Load compliance rules from YAML."""
    path = Path(rules_path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("compliance_rules", [])


def _build_engine(settings: Settings, rules: list[dict]) -> tuple[ReviewEngine, Retriever | None]:
    """Build the review engine with all dependencies."""
    discover_plugins()
    llm = LLMClient(settings)
    prompt_builder = PromptBuilder(
        prompts_dir=settings.prompts_dir,
        max_context_tokens=settings.llm_max_output_tokens,
    )

    # Set up RAG (optional, supports precomputed mode for zero-model retrieval)
    retriever = None
    vectorstore_path = Path(settings.vectorstore_path)
    if settings.rag_mode != "disabled" and vectorstore_path.exists() and any(vectorstore_path.iterdir()):
        try:
            vectorstore = VectorStore(settings.vectorstore_path)
            if vectorstore.count > 0:
                precomputed = PrecomputedQueries(settings.precomputed_queries_path)
                # Always try to load embedder for fallback capability;
                # gracefully degrade if Ollama is not running
                embedder = None
                try:
                    embedder = Embedder(settings)
                except Exception as emb_err:
                    if settings.rag_mode == "runtime_embed":
                        console.print(f"[yellow]Embedding model unavailable, falling back to precomputed: {emb_err}[/yellow]")
                    else:
                        logger.debug("Embedder not loaded (optional in %s mode): %s", settings.rag_mode, emb_err)

                retriever = Retriever(
                    vectorstore=vectorstore,
                    top_k=settings.retrieval_top_k,
                    embedder=embedder,
                    precomputed=precomputed,
                    mode=settings.rag_mode,
                )
                mode_label = "precomputed" if precomputed.is_available else "runtime_embed"
                console.print(f"[dim]RAG loaded (mode={mode_label}, vectors={vectorstore.count})[/dim]")
        except Exception as e:
            console.print(f"[yellow]RAG not available: {e}[/yellow]")

    engine = ReviewEngine(
        llm=llm,
        retriever=retriever,
        prompt_builder=prompt_builder,
        settings=settings,
        rules=rules,
    )
    return engine, retriever


@app.command()
def review(
    contract_path: Annotated[str, typer.Argument(help="合同文件路径 (.pdf/.docx/.txt)")],
    rules: Annotated[Optional[str], typer.Option("--rules", "-r", help="自定义规则文件")] = None,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="输出文件路径")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="输出格式")] = "markdown",
    dimensions: Annotated[Optional[list[str]], typer.Option("--dim", "-d", help="审查维度")] = None,
    model: Annotated[Optional[str], typer.Option("--model", "-m", help="LLM 模型")] = None,
    ocr: Annotated[bool, typer.Option("--ocr/--no-ocr", help="启用 OCR（扫描件识别）")] = False,
    audit_log: Annotated[Optional[str], typer.Option("--audit-log", help="审计日志输出路径")] = None,
) -> None:
    """审查一份合同文件。"""
    settings = Settings()
    if model:
        settings.llm_model = model
    if ocr:
        settings.ocr_enabled = True

    rules_path = rules or settings.rules_path
    rule_list = _load_rules(rules_path)

    # Track rule file changes
    if rule_history.check_and_record(rules_path):
        console.print("[dim]规则文件已变更，版本已记录[/dim]")

    # Set up OCR engine if enabled
    ocr_engine = create_ocr_engine(settings)
    if ocr_engine:
        console.print(f"[dim]OCR enabled: {settings.ocr_provider}[/dim]")

    # Parse contract (async if OCR is available)
    parser = ContractParser(ocr_engine=ocr_engine)
    with console.status("解析合同文档..."):
        if ocr_engine:
            contract = asyncio.run(parser.parse_async(contract_path))
        else:
            contract = parser.parse(contract_path)
        splitter = ContractSplitter(settings.chunk_size_tokens, settings.chunk_overlap_tokens)
        chunks = splitter.split(contract)

    ocr_label = ""
    if contract.metadata.get("ocr_used"):
        ocr_label = f" (OCR: {contract.metadata.get('ocr_provider')}, confidence={contract.metadata.get('ocr_confidence', 0):.2f})"
    console.print(f"合同已解析: {len(contract.sections)} 个章节, {len(chunks)} 个分块{ocr_label}")

    # Build engine
    engine, _ = _build_engine(settings, rule_list)

    # Run review
    def on_progress(event: ProgressEvent) -> None:
        if event.status == "started":
            console.print(f"  [cyan]▶ {event.dimension}[/cyan]")
        elif event.status == "completed":
            console.print(f"  [green]✓ {event.dimension}[/green]")

    console.print("\n[bold]开始审查...[/bold]")
    report = asyncio.run(
        engine.review(contract, dimensions=dimensions, on_progress=on_progress)
    )

    # Format output
    if fmt == "json":
        result = report.model_dump_json(indent=2, ensure_ascii=False)
    else:
        result = format_report_markdown(report)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        console.print(f"\n[green]报告已保存: {output}[/green]")
    else:
        console.print()
        if fmt == "markdown":
            from rich.markdown import Markdown
            console.print(Markdown(result))
        else:
            console.print(result)

    # Save audit trail if requested
    audit_trail = getattr(engine, "_last_audit_trail", None)
    if audit_trail and audit_log:
        audit_trail.save(Path(audit_log))
        console.print(f"[dim]审计日志已保存: {audit_log}[/dim]")

    # Summary panel
    console.print(Panel(
        f"风险评分: {report.overall_risk_score}/100 ({report.risk_score_label()})",
        title="审查完成",
        style="bold green" if report.overall_risk_score < 40 else "bold yellow" if report.overall_risk_score < 70 else "bold red",
    ))


@app.command()
def batch(
    directory: Annotated[str, typer.Argument(help="包含合同文件的目录")],
    output_dir: Annotated[str, typer.Option("--output", "-o", help="报告输出目录")] = "./reports",
    fmt: Annotated[str, typer.Option("--format", "-f")] = "markdown",
    model: Annotated[Optional[str], typer.Option("--model", "-m")] = None,
) -> None:
    """批量审查目录中的所有合同。"""
    settings = Settings()
    if model:
        settings.llm_model = model

    rule_list = _load_rules(settings.rules_path)
    engine, _ = _build_engine(settings, rule_list)

    # Find contract files
    dir_path = Path(directory)
    files = list(dir_path.glob("*.pdf")) + list(dir_path.glob("*.docx")) + list(dir_path.glob("*.txt"))
    if not files:
        console.print("[red]未找到合同文件[/red]")
        raise typer.Exit(1)

    console.print(f"找到 {len(files)} 份合同")

    reports = asyncio.run(
        batch_review([str(f) for f in files], engine, settings)
    )

    # Save reports
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for report in reports:
        if fmt == "json":
            content = report.model_dump_json(indent=2, ensure_ascii=False)
            ext = ".json"
        else:
            content = format_report_markdown(report)
            ext = ".md"
        report_path = out / f"{report.contract_name}_report{ext}"
        report_path.write_text(content, encoding="utf-8")

    console.print(f"\n[green]{len(reports)} 份报告已保存到 {output_dir}[/green]")


@app.command()
def ingest(
    knowledge_dir: Annotated[str, typer.Argument(help="法律知识库目录")] = "knowledge_base",
    source_type: Annotated[str, typer.Option("--type", "-t")] = "civil_code",
) -> None:
    """将法律知识库灌入向量数据库。"""
    settings = Settings()
    embedder = Embedder(settings)
    vectorstore = VectorStore(settings.vectorstore_path)
    ingestor = KnowledgeIngestor(embedder, vectorstore)

    with console.status(f"正在灌入知识库: {knowledge_dir}"):
        added = asyncio.run(ingestor.ingest_directory(knowledge_dir, source_type))

    console.print(f"[green]已添加 {added} 个知识块, 总计 {vectorstore.count} 个[/green]")


@app.command("accept-rule")
def accept_rule(
    report_path: Annotated[str, typer.Argument(help="审查报告 JSON 文件路径")],
    rule_id: Annotated[Optional[str], typer.Option("--id", help="指定候选规则 ID（省略则交互选择）")] = None,
    rules_file: Annotated[Optional[str], typer.Option("--rules", "-r", help="目标规则文件")] = None,
    all_rules: Annotated[bool, typer.Option("--all", help="接受所有候选规则")] = False,
) -> None:
    """将审查报告中的候选规则纳入规则库。"""
    # 加载报告
    report_file = Path(report_path)
    if not report_file.exists():
        console.print(f"[red]报告文件不存在: {report_path}[/red]")
        raise typer.Exit(1)

    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    candidates = report_data.get("candidate_rules", [])
    if not candidates:
        console.print("[yellow]报告中无候选规则[/yellow]")
        raise typer.Exit(0)

    # 选择要接受的规则
    if all_rules:
        selected = candidates
    elif rule_id:
        selected = [c for c in candidates if c["id"] == rule_id]
        if not selected:
            console.print(f"[red]未找到候选规则: {rule_id}[/red]")
            console.print("可用候选规则:")
            for c in candidates:
                console.print(f"  {c['id']}: {c.get('description', '')[:80]}")
            raise typer.Exit(1)
    else:
        # 展示候选规则供用户确认
        console.print("[bold]候选规则:[/bold]\n")
        for i, c in enumerate(candidates, 1):
            console.print(f"  {i}. [{c.get('severity', 'medium').upper()}] {c['id']}")
            console.print(f"     {c.get('description', '')[:100]}")
            if c.get("evidence_example"):
                console.print(f"     [dim]示例: {c['evidence_example'][:80]}...[/dim]")
            console.print()

        choice = typer.prompt("输入序号（逗号分隔，或 'all'）", default="all")
        if choice.strip().lower() == "all":
            selected = candidates
        else:
            indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
            selected = [candidates[i] for i in indices if 0 <= i < len(candidates)]

    if not selected:
        console.print("[yellow]未选择任何规则[/yellow]")
        raise typer.Exit(0)

    # 加载目标规则文件
    settings = Settings()
    target_path = Path(rules_file or settings.rules_path)
    if not target_path.exists():
        console.print(f"[red]规则文件不存在: {target_path}[/red]")
        raise typer.Exit(1)

    with open(target_path, encoding="utf-8") as f:
        rules_data = yaml.safe_load(f)

    existing_ids = {r["id"] for r in rules_data.get("compliance_rules", [])}

    # 追加新规则
    added = 0
    from datetime import date
    for candidate in selected:
        if candidate["id"] in existing_ids:
            console.print(f"  [yellow]跳过（已存在）: {candidate['id']}[/yellow]")
            continue
        new_rule = {
            "id": candidate["id"],
            "description": candidate.get("description", ""),
            "category": candidate.get("category", "general"),
            "severity": candidate.get("severity", "medium"),
            "added_date": date.today().isoformat(),
            "source": "auto_discovered",
        }
        rules_data["compliance_rules"].append(new_rule)
        added += 1
        console.print(f"  [green]✓ 已添加: {candidate['id']}[/green]")

    if added > 0:
        with open(target_path, "w", encoding="utf-8") as f:
            yaml.dump(rules_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        console.print(f"\n[green]{added} 条规则已写入 {target_path}[/green]")

        # 记录规则文件变更
        if rule_history.check_and_record(str(target_path)):
            console.print("[dim]规则文件版本已记录[/dim]")
    else:
        console.print("[yellow]无新规则添加[/yellow]")


@app.command("audit-summary")
def audit_summary(
    audit_path: Annotated[str, typer.Argument(help="审计日志 JSONL 文件路径")],
    contract: Annotated[Optional[str], typer.Option("--contract", "-c", help="按合同名称过滤")] = None,
) -> None:
    """查看审计日志的人类可读摘要。"""
    path = Path(audit_path)
    if not path.exists():
        console.print(f"[red]审计日志不存在: {audit_path}[/red]")
        raise typer.Exit(1)

    # 解析 JSONL
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if not entries:
        console.print("[yellow]审计日志为空[/yellow]")
        raise typer.Exit(0)

    # 按合同分组
    contracts: dict[str, list[dict]] = {}
    for entry in entries:
        name = entry.get("contract", "unknown")
        if contract and contract != name:
            continue
        contracts.setdefault(name, []).append(entry)

    if not contracts:
        console.print(f"[yellow]未找到合同: {contract}[/yellow]")
        raise typer.Exit(0)

    for name, events in contracts.items():
        console.print(Panel(f"[bold]{name}[/bold]", style="blue"))

        # 事件统计
        event_counts: dict[str, int] = {}
        for e in events:
            evt = e.get("event", "unknown")
            event_counts[evt] = event_counts.get(evt, 0) + 1

        console.print(f"  总事件数: {len(events)}")
        for evt, count in sorted(event_counts.items()):
            console.print(f"  · {evt}: {count}")

        # LLM 调用统计
        llm_calls = [e for e in events if e.get("event") == "llm_call"]
        if llm_calls:
            prompt_tokens = sum(e.get("detail", {}).get("prompt_tokens", 0) for e in llm_calls)
            completion_tokens = sum(e.get("detail", {}).get("completion_tokens", 0) for e in llm_calls)
            cache_hits = sum(1 for e in llm_calls if e.get("detail", {}).get("cached"))
            console.print(f"\n  LLM 调用: {len(llm_calls)} 次 (缓存命中: {cache_hits})")
            console.print(f"  Token 消耗: prompt={prompt_tokens:,} + completion={completion_tokens:,} = {prompt_tokens + completion_tokens:,}")

        # 维度结果
        dim_events = [e for e in events if e.get("event") == "review_complete"]
        for de in dim_events:
            detail = de.get("detail", {})
            succeeded = detail.get("dimensions_succeeded", [])
            failed = detail.get("dimensions_failed", [])
            score = detail.get("overall_risk_score", "?")
            console.print(f"\n  风险评分: {score}/100")
            if succeeded:
                console.print(f"  成功维度: {', '.join(succeeded)}")
            if failed:
                console.print(f"  [red]失败维度: {', '.join(failed)}[/red]")

        # 验证结果
        verif_events = [e for e in events if e.get("event") == "verification_complete"]
        for ve in verif_events:
            d = ve.get("detail", {})
            console.print(f"\n  证据验证: ✓{d.get('evidence_verified', 0)} "
                          f"✗{d.get('evidence_unverified', 0)} "
                          f"?{d.get('evidence_missing', 0)}")
            if d.get("contradictions"):
                for c in d["contradictions"]:
                    console.print(f"  [red]  {c}[/red]")

        # 候选规则
        rule_events = [e for e in events if e.get("event") == "candidate_rules"]
        for re_ in rule_events:
            ids = re_.get("detail", {}).get("ids", [])
            if ids:
                console.print(f"\n  候选新规则: {', '.join(ids)}")

        console.print()


if __name__ == "__main__":
    app()
