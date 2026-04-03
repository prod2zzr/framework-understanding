"""Factory for creating OCR engine instances from configuration."""

from contract_reviewer.models.config import Settings
from contract_reviewer.ocr.base import OCREngine


def create_ocr_engine(settings: Settings) -> OCREngine | None:
    """Create an OCR engine based on settings. Returns None if OCR is disabled."""
    if not settings.ocr_enabled:
        return None

    if settings.ocr_provider == "paddleocr":
        from contract_reviewer.ocr.paddle_ocr import PaddleOCREngine

        return PaddleOCREngine(
            languages=settings.ocr_languages,
            use_gpu=settings.ocr_use_gpu,
        )
    elif settings.ocr_provider == "glm_ocr":
        from contract_reviewer.ocr.glm_ocr import GLMOCREngine

        return GLMOCREngine(
            api_key=settings.llm_api_key,
            api_base=settings.llm_api_base,
        )
    else:
        raise ValueError(f"Unknown OCR provider: {settings.ocr_provider}")
