"""OCR engine abstractions and data models."""

import time
from abc import ABC, abstractmethod
from platform import node as hostname

from pydantic import BaseModel


class OCRPage(BaseModel):
    """OCR result for a single page."""

    page_num: int
    text: str
    confidence: float = 0.0  # 0.0 - 1.0
    elapsed_ms: int = 0


class OCRResult(BaseModel):
    """Complete OCR result for a document."""

    pages: list[OCRPage]
    provider: str  # "paddleocr" | "glm_ocr"
    total_elapsed_ms: int = 0
    device: str = "local:cpu"  # "local:cpu" | "local:gpu" | "remote:api"
    hostname: str = ""

    @property
    def full_text(self) -> str:
        """Concatenate all page texts."""
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def average_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.confidence for p in self.pages) / len(self.pages)


class OCREngine(ABC):
    """Abstract base class for OCR engines.

    Implementations should handle PDF → text conversion locally,
    keeping contract data on the edge device.
    """

    provider_name: str = ""

    @abstractmethod
    async def recognize(self, pdf_path: str, dpi: int = 300) -> OCRResult:
        """OCR a PDF file and return structured results.

        Args:
            pdf_path: Path to the PDF file.
            dpi: Resolution for PDF-to-image conversion.

        Returns:
            OCRResult with per-page text and metadata.
        """
        ...

    def _make_result(
        self,
        pages: list[OCRPage],
        start_time: float,
        device: str = "local:cpu",
    ) -> OCRResult:
        """Helper to build a consistent OCRResult."""
        elapsed = int((time.time() - start_time) * 1000)
        return OCRResult(
            pages=pages,
            provider=self.provider_name,
            total_elapsed_ms=elapsed,
            device=device,
            hostname=hostname(),
        )
