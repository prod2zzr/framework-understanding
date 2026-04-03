"""GLM-OCR engine (alternative backend).

Strengths (per OmniDocBench):
- Better on Chinese books/textbooks
- Better reading order detection
Weaknesses:
- Unstable response times (100s+ on complex layouts)
- 5-8x worse on handwriting and newspapers
"""

import logging
import time
from pathlib import Path

from contract_reviewer.ocr.base import OCREngine, OCRPage, OCRResult

logger = logging.getLogger(__name__)


class GLMOCREngine(OCREngine):
    """GLM-OCR engine using ZhipuAI API or local model."""

    provider_name = "glm_ocr"

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        self.api_base = api_base

    async def recognize(self, pdf_path: str, dpi: int = 300) -> OCRResult:
        """OCR a PDF using GLM-OCR via API."""
        start_time = time.time()

        images = self._pdf_to_images(pdf_path, dpi)
        pages: list[OCRPage] = []

        for i, img_path in enumerate(images):
            page_start = time.time()
            try:
                text = await self._call_glm_api(img_path)
                confidence = 0.8  # GLM API doesn't return per-line confidence
            except Exception as e:
                logger.warning("GLM-OCR failed on page %d: %s", i + 1, e)
                text, confidence = "", 0.0

            elapsed = int((time.time() - page_start) * 1000)
            pages.append(OCRPage(
                page_num=i + 1,
                text=text,
                confidence=confidence,
                elapsed_ms=elapsed,
            ))

        return self._make_result(pages, start_time, "remote:api")

    async def _call_glm_api(self, image_path: Path) -> str:
        """Call GLM-OCR API with an image. Uses LiteLLM for unified interface."""
        import base64
        import litellm

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        response = await litellm.acompletion(
            model="zhipu/glm-ocr",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "请识别图片中的所有文字，保持原始排版格式输出。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }],
            api_key=self.api_key,
            api_base=self.api_base,
            timeout=120,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _pdf_to_images(pdf_path: str, dpi: int) -> list[Path]:
        """Convert PDF pages to images."""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError("pdf2image is not installed. Install with: pip install pdf2image")

        import tempfile

        output_dir = tempfile.mkdtemp(prefix="ocr_glm_")
        images = convert_from_path(pdf_path, dpi=dpi, output_folder=output_dir, fmt="png")
        paths = []
        for i, img in enumerate(images):
            path = Path(output_dir) / f"page_{i}.png"
            img.save(str(path))
            paths.append(path)
        return paths
