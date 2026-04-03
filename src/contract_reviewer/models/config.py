"""Application settings with environment variable override support."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_model: str = "anthropic/claude-sonnet-4-20250514"
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_max_total_tokens: int = 1_000_000
    llm_max_concurrent: int = 5
    llm_temperature: float = 0.1
    llm_max_output_tokens: int = 4096

    # Embeddings
    embedding_model: str = "ollama/bge-large-zh"
    embedding_api_base: str = "http://localhost:11434"

    # RAG
    vectorstore_path: str = "./data/chroma"
    retrieval_top_k: int = 5
    use_reranker: bool = False
    reranker_model: str | None = None
    rag_mode: str = "precomputed"  # "precomputed" | "runtime_embed" | "disabled"
    precomputed_queries_path: str = "data/precomputed_queries.json"

    # Chunking
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64

    # Cache
    cache_enabled: bool = True
    cache_dir: str = "./data/cache"

    # Review
    review_dimensions: list[str] = [
        "risk_analysis",
        "compliance",
        "completeness",
        "term_fairness",
    ]

    # OCR (edge deployment)
    ocr_enabled: bool = False
    ocr_provider: str = "paddleocr"  # "paddleocr" | "glm_ocr"
    ocr_languages: list[str] = ["ch", "en"]
    ocr_use_gpu: bool = False
    ocr_dpi: int = 300
    ocr_result_endpoint: str | None = None  # Layer 3 aggregation endpoint

    # Paths
    prompts_dir: str = "config/prompts"
    rules_path: str = "config/rules/default_rules.yaml"

    model_config = {"env_prefix": "CR_"}
