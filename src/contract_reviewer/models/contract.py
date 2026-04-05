"""Contract document data models."""

from pydantic import BaseModel


class Section(BaseModel):
    """A structural section of a contract (e.g., an article or clause)."""

    heading: str = ""
    body: str = ""
    section_type: str = "body"  # "title", "parties", "body", "signature", "table"
    index: int = 0


class ContractChunk(BaseModel):
    """A chunk of contract text for LLM processing."""

    text: str
    chunk_index: int
    total_chunks: int
    section_heading: str = ""
    clause_number: str = ""
    metadata: dict = {}


class Contract(BaseModel):
    """A parsed contract document."""

    name: str
    source_path: str
    full_text: str
    sections: list[Section] = []
    chunks: list[ContractChunk] = []
    metadata: dict = {}
