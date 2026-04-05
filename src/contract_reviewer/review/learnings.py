"""Candidate rule extraction — institutional memory from review findings.

After a review completes, identifies findings that don't match existing rules
and formats them as candidate rules for human review.
"""

import logging
from difflib import SequenceMatcher

from contract_reviewer.models.review import RiskFinding, Severity

logger = logging.getLogger(__name__)


def extract_candidate_rules(
    findings: list[RiskFinding],
    existing_rules: list[dict],
    min_severity: Severity = Severity.MEDIUM,
) -> list[dict]:
    """Find review findings that aren't covered by existing rules.

    Returns candidate rule dicts suitable for appending to default_rules.yaml.
    Only considers findings with severity >= *min_severity*.
    """
    if not findings or not existing_rules:
        return []

    # Build a lookup of existing rule descriptions for matching
    existing_descriptions = [
        r.get("description", "") + " " + r.get("description_en", "")
        for r in existing_rules
    ]

    severity_order = [Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    min_idx = severity_order.index(min_severity)
    qualifying_severities = set(severity_order[: min_idx + 1])

    candidates: list[dict] = []
    seen_types: set[str] = set()

    for finding in findings:
        if finding.severity not in qualifying_severities:
            continue
        if finding.risk_type in seen_types:
            continue

        # Check if this finding is already covered by an existing rule
        if _matches_existing_rule(finding, existing_descriptions):
            continue

        seen_types.add(finding.risk_type)
        candidates.append({
            "id": f"AUTO_{finding.risk_type.upper().replace(' ', '_')[:30]}",
            "description": finding.explanation[:120],
            "category": _infer_category(finding.risk_type),
            "severity": finding.severity.value,
            "source": "auto_discovered",
            "evidence_example": finding.clause_text[:200] if finding.clause_text else "",
        })

    if candidates:
        logger.info("Extracted %d candidate rules from review findings", len(candidates))

    return candidates


def _matches_existing_rule(
    finding: RiskFinding,
    existing_descriptions: list[str],
    threshold: float = 0.5,
) -> bool:
    """Check if a finding is already substantially covered by an existing rule."""
    finding_text = f"{finding.risk_type} {finding.explanation}"
    for desc in existing_descriptions:
        if SequenceMatcher(None, finding_text[:100], desc[:100]).ratio() > threshold:
            return True
    return False


def _infer_category(risk_type: str) -> str:
    """Best-effort category inference from risk_type string."""
    rt = risk_type.lower()
    category_keywords = {
        "liability": ["liability", "赔偿", "责任", "损失"],
        "penalty": ["penalty", "违约金", "罚金"],
        "termination": ["termination", "解除", "终止"],
        "payment": ["payment", "付款", "支付"],
        "confidentiality": ["confidential", "保密"],
        "intellectual_property": ["ip", "知识产权", "版权", "专利"],
        "dispute": ["dispute", "争议", "仲裁", "诉讼"],
    }
    for category, keywords in category_keywords.items():
        if any(kw in rt for kw in keywords):
            return category
    return "general"
