"""Edge OCR worker with result submission interface.

Handles local OCR processing and (optionally) submits results
to a central aggregation service. Designed for distributed deployment
where contract data stays on the edge device.
"""

import json
import logging
from pathlib import Path

from contract_reviewer.ocr.base import OCREngine, OCRResult

logger = logging.getLogger(__name__)


class OCRWorker:
    """Edge node worker for distributed OCR processing.

    Architecture:
    - Contract PDF stays on local machine (security)
    - OCR runs locally using 0.9B model (no GPU server needed)
    - Only OCR text (not original document) is optionally submitted upstream
    """

    def __init__(self, engine: OCREngine, result_endpoint: str | None = None):
        self.engine = engine
        self.result_endpoint = result_endpoint

    async def process_local(self, pdf_path: str, dpi: int = 300) -> OCRResult:
        """Process a PDF locally and return OCR result."""
        logger.info("Processing locally: %s", pdf_path)
        result = await self.engine.recognize(pdf_path, dpi=dpi)
        logger.info(
            "OCR complete: %d pages, avg confidence=%.2f, elapsed=%dms",
            len(result.pages),
            result.average_confidence,
            result.total_elapsed_ms,
        )
        return result

    async def process_and_submit(self, pdf_path: str, dpi: int = 300) -> OCRResult:
        """Process locally, then submit result to aggregation endpoint."""
        result = await self.process_local(pdf_path, dpi)

        if self.result_endpoint:
            await self._submit_result(result, pdf_path)

        return result

    async def _submit_result(self, result: OCRResult, source_path: str) -> None:
        """Submit OCR result (text only, not original document) to aggregation service."""
        if not self.result_endpoint:
            return

        try:
            import httpx

            payload = {
                "source_filename": Path(source_path).name,
                "ocr_result": result.model_dump(),
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self.result_endpoint, json=payload)
                resp.raise_for_status()
                logger.info("Result submitted to %s", self.result_endpoint)
        except ImportError:
            logger.warning("httpx not installed, cannot submit results. Install with: pip install httpx")
        except Exception as e:
            # Non-fatal: local result is still valid
            logger.warning("Failed to submit result to %s: %s", self.result_endpoint, e)

    def unload_engine(self) -> None:
        """Release OCR model memory (for staged loading pattern)."""
        if hasattr(self.engine, "unload"):
            self.engine.unload()
            logger.info("OCR engine unloaded from memory")
