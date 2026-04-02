"""Built-in plugin for Chinese Civil Code (民法典) compliance checking."""

from contract_reviewer.llm.client import LLMClient
from contract_reviewer.models.contract import ContractChunk
from contract_reviewer.models.review import RiskFinding, Severity
from contract_reviewer.plugins.base import ReviewPlugin
from contract_reviewer.rag.retriever import RetrievedContext


class CivilCodeCompliancePlugin(ReviewPlugin):
    name = "compliance_civil_code"
    version = "0.1.0"
    description = "Check contract clauses against Chinese Civil Code requirements"

    # Key Civil Code rules for contracts (民法典合同编)
    CIVIL_CODE_CHECKS = [
        {
            "article": "第四百九十六条",
            "rule": "格式条款提供方应采取合理方式提示对方注意重大利害关系条款",
            "keywords": ["格式条款", "标准条款", "standard terms"],
        },
        {
            "article": "第五百八十五条",
            "rule": "约定的违约金过分高于造成的损失的，人民法院或仲裁机构可以适当减少",
            "keywords": ["违约金", "penalty", "liquidated damages"],
        },
        {
            "article": "第四百九十七条",
            "rule": "格式条款不合理地免除或减轻提供方责任、加重对方责任的无效",
            "keywords": ["免责", "免除责任", "exemption"],
        },
    ]

    async def review_chunk(
        self,
        chunk: ContractChunk,
        context: list[RetrievedContext],
        llm: LLMClient,
    ) -> list[RiskFinding]:
        findings = []
        text = chunk.text

        for check in self.CIVIL_CODE_CHECKS:
            if any(kw in text for kw in check["keywords"]):
                findings.append(
                    RiskFinding(
                        clause_text=text[:200],
                        risk_type="civil_code_compliance",
                        severity=Severity.MEDIUM,
                        explanation=f"涉及{check['article']}规定: {check['rule']}",
                        suggestion=f"请确保该条款符合{check['article']}的要求",
                    )
                )

        return findings


plugin = CivilCodeCompliancePlugin()
