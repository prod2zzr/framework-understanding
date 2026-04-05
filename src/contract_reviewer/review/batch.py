"""Batch contract processing with concurrency control."""

import asyncio
import logging
from pathlib import Path

from contract_reviewer.chunking.contract_parser import ContractParser
from contract_reviewer.chunking.splitter import ContractSplitter
from contract_reviewer.models.config import Settings
from contract_reviewer.models.review import ReviewReport
from contract_reviewer.review.engine import ReviewEngine

logger = logging.getLogger(__name__)


async def batch_review(
    file_paths: list[str],
    engine: ReviewEngine,
    settings: Settings,
    max_concurrent_contracts: int = 3,
) -> list[ReviewReport]:
    """Review multiple contracts concurrently.

    Args:
        file_paths: List of contract file paths.
        engine: Configured ReviewEngine.
        settings: Application settings.
        max_concurrent_contracts: Max contracts to process in parallel.
    """
    parser = ContractParser()
    splitter = ContractSplitter(
        chunk_size=settings.chunk_size_tokens,
        overlap=settings.chunk_overlap_tokens,
    )
    semaphore = asyncio.Semaphore(max_concurrent_contracts)

    async def review_one(path: str) -> ReviewReport:
        async with semaphore:
            logger.info("Starting review: %s", path)
            contract = parser.parse(path)
            splitter.split(contract)
            report = await engine.review(contract)
            logger.info("Completed review: %s (score=%d)", path, report.overall_risk_score)
            return report

    tasks = [review_one(p) for p in file_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    reports: list[ReviewReport] = []
    for path, result in zip(file_paths, results):
        if isinstance(result, Exception):
            logger.error("Failed to review %s: %s", path, result)
            reports.append(
                ReviewReport(
                    contract_name=Path(path).stem,
                    overall_risk_score=0,
                    summary=f"审核失败: {result}",
                )
            )
        else:
            reports.append(result)

    return reports
