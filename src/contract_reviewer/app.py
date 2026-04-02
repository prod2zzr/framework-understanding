"""FastAPI application for contract review API."""

import asyncio
import json
import tempfile
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from contract_reviewer.chunking.contract_parser import ContractParser
from contract_reviewer.chunking.splitter import ContractSplitter
from contract_reviewer.llm.client import LLMClient
from contract_reviewer.models.config import Settings
from contract_reviewer.models.progress import ProgressEvent
from contract_reviewer.models.review import ReviewReport
from contract_reviewer.rag.embedder import Embedder
from contract_reviewer.rag.prompt_builder import PromptBuilder
from contract_reviewer.rag.retriever import Retriever
from contract_reviewer.rag.vectorstore import VectorStore
from contract_reviewer.review.aggregator import format_report_markdown
from contract_reviewer.review.engine import ReviewEngine

app = FastAPI(
    title="Contract Reviewer API",
    description="AI 合同审核服务 — 支持云端/本地模型",
    version="0.1.0",
)

# Globals initialized on startup
_settings: Settings | None = None
_engine: ReviewEngine | None = None


@app.on_event("startup")
async def startup() -> None:
    global _settings, _engine
    _settings = Settings()

    rules_path = Path(_settings.rules_path)
    rules = []
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        rules = data.get("compliance_rules", [])

    llm = LLMClient(_settings)
    prompt_builder = PromptBuilder(
        prompts_dir=_settings.prompts_dir,
        max_context_tokens=_settings.llm_max_output_tokens,
    )

    retriever = None
    vs_path = Path(_settings.vectorstore_path)
    if vs_path.exists():
        try:
            embedder = Embedder(_settings)
            vectorstore = VectorStore(_settings.vectorstore_path)
            if vectorstore.count > 0:
                retriever = Retriever(embedder, vectorstore, _settings.retrieval_top_k)
        except Exception:
            pass

    _engine = ReviewEngine(
        llm=llm,
        retriever=retriever,
        prompt_builder=prompt_builder,
        settings=_settings,
        rules=rules,
    )


@app.post("/api/review", response_model=ReviewReport)
async def review_contract(
    file: UploadFile = File(...),
    dimensions: list[str] | None = Query(default=None),
) -> ReviewReport:
    """Upload and review a contract. Returns structured JSON report."""
    if _engine is None or _settings is None:
        raise HTTPException(503, "Service not initialized")

    # Save uploaded file
    suffix = Path(file.filename or "contract.txt").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        parser = ContractParser()
        contract = parser.parse(tmp_path)
        splitter = ContractSplitter(_settings.chunk_size_tokens, _settings.chunk_overlap_tokens)
        splitter.split(contract)

        report = await _engine.review(contract, dimensions=dimensions)
        return report
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/review/stream")
async def review_contract_stream(
    file: UploadFile = File(...),
    dimensions: list[str] | None = Query(default=None),
) -> EventSourceResponse:
    """Upload and review with SSE streaming progress."""
    if _engine is None or _settings is None:
        raise HTTPException(503, "Service not initialized")

    suffix = Path(file.filename or "contract.txt").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    async def generate():
        try:
            parser = ContractParser()
            contract = parser.parse(tmp_path)
            splitter = ContractSplitter(_settings.chunk_size_tokens, _settings.chunk_overlap_tokens)
            splitter.split(contract)

            progress_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

            async def on_progress(event: ProgressEvent) -> None:
                await progress_queue.put(event)

            # Run review in background
            review_task = asyncio.create_task(
                _engine.review(contract, dimensions=dimensions, on_progress=on_progress)
            )

            # Stream progress events
            while True:
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    if event is None:
                        break
                    yield {
                        "event": event.status,
                        "data": json.dumps(event.model_dump(), ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    if review_task.done():
                        break

            report = await review_task
            yield {
                "event": "report",
                "data": report.model_dump_json(ensure_ascii=False),
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return EventSourceResponse(generate())


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model": _settings.llm_model if _settings else "not initialized",
        "rag_available": _engine is not None and _engine.retriever is not None,
    }
