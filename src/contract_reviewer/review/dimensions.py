"""Built-in review dimension definitions."""

from dataclasses import dataclass, field


@dataclass
class DimensionSpec:
    """Specification for a review dimension."""

    name: str
    name_zh: str
    description: str
    prompt_template: str
    topic_filter: str | None = None  # For RAG retrieval filtering
    applicable_section_types: list[str] | None = None  # None = all sections


DIMENSIONS: dict[str, DimensionSpec] = {
    "risk_analysis": DimensionSpec(
        name="risk_analysis",
        name_zh="风险分析",
        description="Identify clauses that pose legal or financial risk",
        prompt_template="risk_analysis.jinja2",
        topic_filter="liability",
        applicable_section_types=None,  # Check all sections for risks
    ),
    "compliance": DimensionSpec(
        name="compliance",
        name_zh="合规性检查",
        description="Check compliance with civil code and relevant regulations",
        prompt_template="compliance_check.jinja2",
        topic_filter=None,  # Use rule-specific topics
    ),
    "completeness": DimensionSpec(
        name="completeness",
        name_zh="完整性检查",
        description="Check for missing standard clauses",
        prompt_template="completeness_check.jinja2",
        topic_filter=None,
    ),
    "term_fairness": DimensionSpec(
        name="term_fairness",
        name_zh="条款公平性",
        description="Identify one-sided or unfair terms",
        prompt_template="term_fairness.jinja2",
        topic_filter="fairness",
    ),
}
