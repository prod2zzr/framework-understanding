"""Built-in plugin for risk clause detection."""

from contract_reviewer.llm.client import LLMClient
from contract_reviewer.models.contract import ContractChunk
from contract_reviewer.models.review import RiskFinding, Severity
from contract_reviewer.plugins.base import ReviewPlugin
from contract_reviewer.rag.retriever import RetrievedContext


class RiskClausesPlugin(ReviewPlugin):
    name = "risk_clauses"
    version = "0.1.0"
    description = "Detect risky clauses using pattern matching and LLM analysis"

    # Known high-risk patterns in Chinese contracts
    HIGH_RISK_PATTERNS = [
        ("一切损失", "unlimited_liability", "无限责任条款"),
        ("不可撤销", "irrevocable", "不可撤销承诺"),
        ("单方面解除", "unilateral_termination", "单方解除权"),
        ("自动续期", "auto_renewal", "自动续期条款"),
        ("放弃诉讼权利", "waive_litigation", "放弃诉权"),
        ("独家", "exclusivity", "排他性条款"),
    ]

    async def review_chunk(
        self,
        chunk: ContractChunk,
        context: list[RetrievedContext],
        llm: LLMClient,
    ) -> list[RiskFinding]:
        findings = []
        text = chunk.text

        # Pattern-based quick scan
        for pattern, risk_type, desc in self.HIGH_RISK_PATTERNS:
            if pattern in text:
                findings.append(
                    RiskFinding(
                        clause_text=self._extract_context(text, pattern),
                        risk_type=risk_type,
                        severity=Severity.MEDIUM,
                        explanation=f"检测到潜在风险模式: {desc}",
                        suggestion=f"建议仔细审查包含「{pattern}」的条款",
                    )
                )

        return findings

    @staticmethod
    def _extract_context(text: str, keyword: str, window: int = 100) -> str:
        """Extract text surrounding a keyword."""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]


plugin = RiskClausesPlugin()
