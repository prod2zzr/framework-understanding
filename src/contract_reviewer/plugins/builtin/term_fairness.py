"""Built-in plugin for term fairness detection."""

from contract_reviewer.llm.client import LLMClient
from contract_reviewer.models.contract import ContractChunk
from contract_reviewer.models.review import RiskFinding, Severity
from contract_reviewer.plugins.base import ReviewPlugin
from contract_reviewer.rag.retriever import RetrievedContext


class TermFairnessPlugin(ReviewPlugin):
    name = "term_fairness"
    version = "0.1.0"
    description = "Detect one-sided or unfair contract terms"

    # Patterns indicating potential unfairness
    UNFAIR_PATTERNS = [
        ("仅甲方有权", "one_sided_right", "单方权利条款——仅甲方享有权利"),
        ("仅乙方承担", "one_sided_liability", "单方义务条款——仅乙方承担责任"),
        ("甲方不承担任何责任", "exemption", "甲方完全免责"),
        ("乙方不得", "restriction", "对乙方的限制性条款"),
        ("最终解释权", "interpretation_right", "最终解释权条款（可能无效）"),
    ]

    async def review_chunk(
        self,
        chunk: ContractChunk,
        context: list[RetrievedContext],
        llm: LLMClient,
    ) -> list[RiskFinding]:
        findings = []
        text = chunk.text

        for pattern, risk_type, desc in self.UNFAIR_PATTERNS:
            if pattern in text:
                findings.append(
                    RiskFinding(
                        clause_text=self._extract_context(text, pattern),
                        risk_type=risk_type,
                        severity=Severity.HIGH,
                        explanation=desc,
                        suggestion="建议修改为对等条款，确保双方权利义务平衡",
                    )
                )

        return findings

    @staticmethod
    def _extract_context(text: str, keyword: str, window: int = 100) -> str:
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]


plugin = TermFairnessPlugin()
