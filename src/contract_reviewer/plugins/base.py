"""Abstract base class for review plugins."""

from abc import ABC, abstractmethod

from contract_reviewer.llm.client import LLMClient
from contract_reviewer.models.contract import ContractChunk
from contract_reviewer.models.review import RiskFinding
from contract_reviewer.rag.retriever import RetrievedContext


class ReviewPlugin(ABC):
    """Base class for custom review plugins."""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    async def review_chunk(
        self,
        chunk: ContractChunk,
        context: list[RetrievedContext],
        llm: LLMClient,
    ) -> list[RiskFinding]:
        """Review a single chunk. Returns list of findings."""
        ...

    def applicable_to(self, chunk: ContractChunk) -> bool:
        """Whether this plugin should process the given chunk."""
        return True
