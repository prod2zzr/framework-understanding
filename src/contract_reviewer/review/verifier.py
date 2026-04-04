"""Independent verification stage for review findings.

Runs after all dimensions complete, before final report generation.
Validates evidence, detects cross-dimension patterns, and flags contradictions.
"""

import logging
from difflib import SequenceMatcher

from contract_reviewer.models.review import (
    ComplianceStatus,
    DimensionResult,
    RiskFinding,
    Severity,
)

logger = logging.getLogger(__name__)

# Minimum clause_text length to be considered meaningful evidence
_MIN_EVIDENCE_LEN = 10
# Fuzzy match threshold for evidence verification
_FUZZY_THRESHOLD = 0.75


class FindingVerifier:
    """Post-dimension verification: evidence check + cross-dimension coordination."""

    def verify_all(
        self,
        dim_results: dict[str, DimensionResult],
        full_text: str,
    ) -> dict:
        """Run all verification steps. Returns a verification summary dict."""
        stats = {
            "evidence_verified": 0,
            "evidence_unverified": 0,
            "evidence_missing": 0,
            "confidence_degraded": 0,
            "cross_dimension_boosts": 0,
            "contradictions": [],
        }

        # Step 1: Verify evidence for each finding
        for dim_result in dim_results.values():
            if not dim_result.success:
                continue
            for risk in dim_result.risks:
                self._verify_evidence(risk, full_text, stats)

        # Step 2: Cross-dimension boost
        stats["cross_dimension_boosts"] = self._cross_dimension_boost(dim_results)

        # Step 3: Detect contradictions
        stats["contradictions"] = self._detect_contradictions(dim_results)

        return stats

    def _verify_evidence(
        self,
        finding: RiskFinding,
        full_text: str,
        stats: dict,
    ) -> None:
        """Check that clause_text actually exists in the contract."""
        if not finding.clause_text or len(finding.clause_text.strip()) < _MIN_EVIDENCE_LEN:
            finding.evidence_verified = False
            finding.confidence = min(finding.confidence, 0.3)
            stats["evidence_missing"] += 1
            return

        clause = finding.clause_text.strip()

        # Exact match
        if clause in full_text:
            finding.evidence_verified = True
            stats["evidence_verified"] += 1
            return

        # Fuzzy match — find the best matching window in full_text
        best_ratio = self._best_fuzzy_ratio(clause, full_text)
        if best_ratio >= _FUZZY_THRESHOLD:
            finding.evidence_verified = True
            stats["evidence_verified"] += 1
        else:
            finding.evidence_verified = False
            finding.confidence *= 0.5
            stats["evidence_unverified"] += 1
            stats["confidence_degraded"] += 1
            logger.info(
                "Evidence unverified (best ratio=%.2f): %.60s...",
                best_ratio,
                finding.clause_text,
            )

    @staticmethod
    def _best_fuzzy_ratio(needle: str, haystack: str) -> float:
        """Slide a window over haystack and return the best SequenceMatcher ratio."""
        if not needle or not haystack:
            return 0.0
        window = len(needle)
        best = 0.0
        # Sample positions to avoid O(n*m) — check every half-window step
        step = max(1, window // 2)
        for start in range(0, max(1, len(haystack) - window + 1), step):
            segment = haystack[start : start + window + window // 4]
            ratio = SequenceMatcher(None, needle, segment).ratio()
            if ratio > best:
                best = ratio
                if best >= _FUZZY_THRESHOLD:
                    return best  # Early exit — good enough
        return best

    def _cross_dimension_boost(
        self,
        dim_results: dict[str, DimensionResult],
    ) -> int:
        """Boost severity when the same clause is flagged by multiple dimensions."""
        # Collect (clause_text, dimension, finding) tuples
        clause_dims: dict[str, list[tuple[str, RiskFinding]]] = {}
        for dim_name, dim_result in dim_results.items():
            if not dim_result.success:
                continue
            for risk in dim_result.risks:
                if not risk.clause_text:
                    continue
                key = risk.clause_text[:80]  # Normalize by prefix
                clause_dims.setdefault(key, []).append((dim_name, risk))

        boost_count = 0
        for key, entries in clause_dims.items():
            dims_involved = {dim for dim, _ in entries}
            if len(dims_involved) >= 2:
                # Boost all findings for this clause
                for _, finding in entries:
                    original = finding.severity
                    if finding.severity == Severity.LOW:
                        finding.severity = Severity.MEDIUM
                    elif finding.severity == Severity.MEDIUM:
                        finding.severity = Severity.HIGH
                    if finding.severity != original:
                        boost_count += 1
                        logger.info(
                            "Cross-dimension boost: %s → %s (dims: %s)",
                            original.value, finding.severity.value,
                            ", ".join(dims_involved),
                        )

        return boost_count

    def _detect_contradictions(
        self,
        dim_results: dict[str, DimensionResult],
    ) -> list[str]:
        """Detect contradictions between dimension results."""
        contradictions: list[str] = []

        # Check: compliance PASS on a rule, but risk_analysis finds HIGH risk
        # on a similar clause
        compliance = dim_results.get("compliance")
        risk_analysis = dim_results.get("risk_analysis")

        if (
            compliance
            and compliance.success
            and risk_analysis
            and risk_analysis.success
        ):
            high_risk_clauses = {
                r.clause_text[:60]
                for r in risk_analysis.risks
                if r.severity == Severity.HIGH and r.clause_text
            }
            for cr in compliance.compliance_results:
                if cr.status == ComplianceStatus.PASS and cr.clause_text:
                    for hrc in high_risk_clauses:
                        if (
                            hrc in cr.clause_text
                            or cr.clause_text[:60] in hrc
                        ):
                            msg = (
                                f"矛盾: compliance 判定 {cr.rule_id} PASS, "
                                f"但 risk_analysis 对相似条款判定为 HIGH 风险"
                            )
                            contradictions.append(msg)
                            logger.warning(msg)

        return contradictions
