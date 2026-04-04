"""Review result data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class RiskFinding(BaseModel):
    """A risk identified in the contract."""

    clause_text: str = Field(description="原文引用")
    risk_type: str = Field(description="风险类型")
    severity: Severity = Field(description="严重程度")
    explanation: str = Field(description="风险分析")
    suggestion: str = Field(description="修改建议")

    # Evidence verification (populated post-analysis, not by LLM)
    evidence_verified: bool = Field(default=False, description="原文引用是否经过验证")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")


class KeyTerm(BaseModel):
    """An extracted key term from the contract."""

    term_type: str = Field(description="条款类型 (parties/date/amount/obligation)")
    value: str = Field(description="提取内容")
    location: str = Field(description="所在位置")


class ComplianceResult(BaseModel):
    """Result of checking one compliance rule."""

    rule_id: str
    rule_description: str
    status: ComplianceStatus
    finding: str = ""
    clause_text: str = ""


class MissingClause(BaseModel):
    """A clause that should be present but is missing."""

    clause_type: str = Field(description="缺失条款类型")
    importance: Severity = Field(description="重要程度")
    description: str = Field(description="条款说明")
    suggestion: str = Field(description="建议补充内容")


class LanguageIssue(BaseModel):
    """A language or ambiguity issue found in the contract."""

    text: str = Field(description="问题文本")
    issue_type: str = Field(description="问题类型 (ambiguity/inconsistency/vague)")
    explanation: str = Field(description="问题说明")
    suggestion: str = Field(description="修改建议")


class DimensionResult(BaseModel):
    """Result from a single review dimension."""

    dimension: str
    success: bool = True
    error: str | None = None
    risks: list[RiskFinding] = []
    key_terms: list[KeyTerm] = []
    compliance_results: list[ComplianceResult] = []
    missing_clauses: list[MissingClause] = []
    language_issues: list[LanguageIssue] = []


class ReviewReport(BaseModel):
    """Complete contract review report."""

    contract_name: str
    review_timestamp: datetime = Field(default_factory=datetime.now)
    overall_risk_score: int = Field(ge=0, le=100, description="0-100, 越高风险越大")
    summary: str = ""
    dimensions: dict[str, DimensionResult] = {}
    verification_summary: dict = Field(default_factory=dict, description="验证摘要")
    audit_summary: dict = Field(default_factory=dict, description="审计摘要")

    def risk_score_label(self) -> str:
        if self.overall_risk_score >= 70:
            return "高风险"
        elif self.overall_risk_score >= 40:
            return "中等风险"
        else:
            return "低风险"
