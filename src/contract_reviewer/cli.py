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
from contract_reviewer.review.engine import ReviewEngine

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
) -> None:
    """审查一份合同文件。"""
    settings = Settings()
    if model:
        settings.llm_model = model
    if ocr:
        settings.ocr_enabled = True

    rules_path = rules or settings.rules_path
    rule_list = _load_rules(rules_path)

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


if __name__ == "__main__":
    app()
