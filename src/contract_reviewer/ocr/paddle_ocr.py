"""PaddleOCR-VL-1.5 local inference engine (default).

Strengths (per OmniDocBench):
- Best overall score across text, tables, formulas
- Stable response times (critical for batch processing)
- 5x better than GLM-OCR on handwritten notes
- 8x better on complex multi-column layouts
"""

import logging
import time
from pathlib import Path

from contract_reviewer.ocr.base import OCREngine, OCRPage, OCRResult

logger = logging.getLogger(__name__)


class PaddleOCREngine(OCREngine):
    """PaddleOCR-VL-1.5 based OCR engine for local inference."""

    provider_name = "paddleocr"

    def __init__(self, languages: list[str] | None = None, use_gpu: bool = False):
        self.languages = languages or ["ch", "en"]
        self.use_gpu = use_gpu
        self._ocr = None

    def _ensure_loaded(self) -> None:
        """Lazy-load PaddleOCR to avoid memory pressure until needed."""
        if self._ocr is not None:
            return

        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise ImportError(
                "PaddleOCR is not installed. "
                "Install with: pip install -e '.[ocr]' "
                "or: pip install paddleocr pdf2image"
            )

        lang = self.languages[0] if self.languages else "ch"
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=self.use_gpu,
            show_log=False,
        )
        logger.info(
            "PaddleOCR loaded (lang=%s, gpu=%s)", lang, self.use_gpu
        )

    def unload(self) -> None:
        """Release model from memory (for staged loading)."""
        self._ocr = None
        logger.info("PaddleOCR unloaded from memory")

    async def recognize(self, pdf_path: str, dpi: int = 300) -> OCRResult:
        """OCR a PDF using PaddleOCR."""
        start_time = time.time()

        images = self._pdf_to_images(pdf_path, dpi)
        self._ensure_loaded()

        pages: list[OCRPage] = []
        for i, img_path in enumerate(images):
            page_start = time.time()
            try:
                result = self._ocr.ocr(str(img_path), cls=True)
                text, confidence = self._parse_paddle_result(result)
            except Exception as e:
                logger.warning("OCR failed on page %d: %s", i + 1, e)
                text, confidence = "", 0.0

            elapsed = int((time.time() - page_start) * 1000)
            pages.append(OCRPage(
                page_num=i + 1,
                text=text,
                confidence=confidence,
                elapsed_ms=elapsed,
            ))

        # Release model if using staged loading pattern
        device = "local:gpu" if self.use_gpu else "local:cpu"
        return self._make_result(pages, start_time, device)

    @staticmethod
    def _pdf_to_images(pdf_path: str, dpi: int) -> list[Path]:
        """Convert PDF pages to images using pdf2image."""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image is not installed. "
                "Install with: pip install pdf2image "
                "Also requires poppler: https://poppler.freedesktop.org/"
            )

        import tempfile

        output_dir = tempfile.mkdtemp(prefix="ocr_")
        images = convert_from_path(pdf_path, dpi=dpi, output_folder=output_dir, fmt="png")
        paths = []
        for i, img in enumerate(images):
            path = Path(output_dir) / f"page_{i}.png"
            img.save(str(path))
            paths.append(path)

        return paths

    @staticmethod
    def _parse_paddle_result(result: list) -> tuple[str, float]:
        """Parse PaddleOCR result into text and average confidence."""
        if not result or not result[0]:
            return "", 0.0

        lines = []
        confidences = []
        for line in result[0]:
            if len(line) >= 2:
                text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                conf = line[1][1] if isinstance(line[1], (list, tuple)) and len(line[1]) > 1 else 0.0
                lines.append(text)
                confidences.append(conf)

        text = "\n".join(lines)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return text, avg_conf
