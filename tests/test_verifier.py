"""Tests for FindingVerifier — evidence check, cross-dimension boost, contradiction detection."""

import pytest

from contract_reviewer.models.review import (
    ComplianceResult,
    ComplianceStatus,
    DimensionResult,
    RiskFinding,
    Severity,
)
from contract_reviewer.review.verifier import FindingVerifier


@pytest.fixture()
def verifier() -> FindingVerifier:
    return FindingVerifier()


FULL_TEXT = (
    "第一条 合同标的\n甲方向乙方提供软件开发服务。\n"
    "第二条 价款与支付\n合同总价为人民币壹佰万元整（¥1,000,000）。"
    "乙方应在收到甲方验收确认后三十日内支付全部款项。\n"
    "第三条 违约责任\n任何一方违约的，应向对方支付合同总价百分之三十的违约金。"
    "因甲方原因导致项目延期的，甲方应承担由此产生的全部损失。"
)


# ── 证据核实 ──────────────────────────────────────────


class TestEvidenceVerification:
    """_verify_evidence 测试。"""

    def test_exact_match_verified(self, verifier: FindingVerifier) -> None:
        """精确匹配原文应标记为已验证。"""
        finding = RiskFinding(
            clause_text="任何一方违约的，应向对方支付合同总价百分之三十的违约金",
            risk_type="违约金过高",
            severity=Severity.HIGH,
            explanation="test",
            suggestion="test",
        )
        dim_results = {"risk_analysis": DimensionResult(dimension="risk_analysis", risks=[finding])}
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert finding.evidence_verified is True
        assert stats["evidence_verified"] == 1

    def test_case_insensitive_match(self, verifier: FindingVerifier) -> None:
        """大小写不敏感匹配应通过（针对英文条款场景）。"""
        text = "Article 1: The Contractor shall deliver the software."
        finding = RiskFinding(
            clause_text="the contractor shall deliver the software",
            risk_type="test",
            severity=Severity.LOW,
            explanation="test",
            suggestion="test",
        )
        dim_results = {"risk_analysis": DimensionResult(dimension="risk_analysis", risks=[finding])}
        verifier.verify_all(dim_results, text)
        assert finding.evidence_verified is True

    def test_short_clause_text_missing(self, verifier: FindingVerifier) -> None:
        """过短的 clause_text (<10字符) 应标记为证据缺失。"""
        finding = RiskFinding(
            clause_text="违约",
            risk_type="test",
            severity=Severity.HIGH,
            explanation="test",
            suggestion="test",
        )
        dim_results = {"risk_analysis": DimensionResult(dimension="risk_analysis", risks=[finding])}
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert finding.evidence_verified is False
        assert finding.confidence <= 0.3
        assert stats["evidence_missing"] == 1

    def test_empty_clause_text(self, verifier: FindingVerifier) -> None:
        """空 clause_text 应标记为证据缺失。"""
        finding = RiskFinding(
            clause_text="",
            risk_type="test",
            severity=Severity.HIGH,
            explanation="test",
            suggestion="test",
        )
        dim_results = {"risk_analysis": DimensionResult(dimension="risk_analysis", risks=[finding])}
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert finding.evidence_verified is False
        assert stats["evidence_missing"] == 1

    def test_fabricated_evidence_unverified(self, verifier: FindingVerifier) -> None:
        """LLM 幻觉生成的条款文本应标记为未验证，置信度降低。"""
        finding = RiskFinding(
            clause_text="本合同第九十九条规定甲方须赔偿全部间接损失及预期利润",
            risk_type="虚构条款",
            severity=Severity.HIGH,
            explanation="test",
            suggestion="test",
        )
        dim_results = {"risk_analysis": DimensionResult(dimension="risk_analysis", risks=[finding])}
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert finding.evidence_verified is False
        assert finding.confidence < 1.0
        assert stats["evidence_unverified"] == 1

    def test_failed_dimension_skipped(self, verifier: FindingVerifier) -> None:
        """失败的维度不应参与验证。"""
        dim_results = {
            "completeness": DimensionResult(dimension="completeness", success=False, error="timeout"),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert stats["evidence_verified"] == 0
        assert stats["evidence_missing"] == 0


# ── 交叉印证 ──────────────────────────────────────────


class TestCrossDimensionBoost:
    """_cross_dimension_boost 测试。"""

    def test_same_clause_two_dimensions_boosts(self, verifier: FindingVerifier) -> None:
        """同一条款被两个维度标记应提升 severity。"""
        clause = "任何一方违约的，应向对方支付合同总价百分之三十的违约金"
        risk1 = RiskFinding(
            clause_text=clause, risk_type="违约金过高",
            severity=Severity.MEDIUM, explanation="t", suggestion="t",
        )
        risk2 = RiskFinding(
            clause_text=clause, risk_type="违约责任不对等",
            severity=Severity.LOW, explanation="t", suggestion="t",
        )
        dim_results = {
            "risk_analysis": DimensionResult(dimension="risk_analysis", risks=[risk1]),
            "term_fairness": DimensionResult(dimension="term_fairness", risks=[risk2]),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert stats["cross_dimension_boosts"] > 0
        # MEDIUM → HIGH, LOW → MEDIUM
        assert risk1.severity == Severity.HIGH
        assert risk2.severity == Severity.MEDIUM

    def test_same_dimension_no_boost(self, verifier: FindingVerifier) -> None:
        """同一维度内的相似发现不应触发 boost。"""
        clause = "任何一方违约的，应向对方支付合同总价百分之三十的违约金"
        risk1 = RiskFinding(
            clause_text=clause, risk_type="a",
            severity=Severity.LOW, explanation="t", suggestion="t",
        )
        risk2 = RiskFinding(
            clause_text=clause, risk_type="b",
            severity=Severity.LOW, explanation="t", suggestion="t",
        )
        dim_results = {
            "risk_analysis": DimensionResult(dimension="risk_analysis", risks=[risk1, risk2]),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert stats["cross_dimension_boosts"] == 0

    def test_high_severity_stays_high(self, verifier: FindingVerifier) -> None:
        """已经是 HIGH 的不应再提升。"""
        clause = "任何一方违约的，应向对方支付合同总价百分之三十的违约金"
        risk1 = RiskFinding(
            clause_text=clause, risk_type="a",
            severity=Severity.HIGH, explanation="t", suggestion="t",
        )
        risk2 = RiskFinding(
            clause_text=clause, risk_type="b",
            severity=Severity.HIGH, explanation="t", suggestion="t",
        )
        dim_results = {
            "risk_analysis": DimensionResult(dimension="risk_analysis", risks=[risk1]),
            "term_fairness": DimensionResult(dimension="term_fairness", risks=[risk2]),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert risk1.severity == Severity.HIGH
        assert risk2.severity == Severity.HIGH
        # boost_count 为 0 — severity 未变
        assert stats["cross_dimension_boosts"] == 0


# ── 矛盾检测 ──────────────────────────────────────────


class TestContradictionDetection:
    """_detect_contradictions 测试。"""

    def test_compliance_pass_but_high_risk_detected(self, verifier: FindingVerifier) -> None:
        """compliance PASS 但 risk_analysis HIGH 应检测到矛盾。"""
        clause = "任何一方违约的，应向对方支付合同总价百分之三十的违约金"
        dim_results = {
            "compliance": DimensionResult(
                dimension="compliance",
                compliance_results=[
                    ComplianceResult(
                        rule_id="R001",
                        rule_description="test",
                        status=ComplianceStatus.PASS,
                        clause_text=clause,
                    ),
                ],
            ),
            "risk_analysis": DimensionResult(
                dimension="risk_analysis",
                risks=[
                    RiskFinding(
                        clause_text=clause,
                        risk_type="test",
                        severity=Severity.HIGH,
                        explanation="t",
                        suggestion="t",
                    ),
                ],
            ),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert len(stats["contradictions"]) > 0
        assert "矛盾" in stats["contradictions"][0]

    def test_no_contradiction_when_compliance_fails(self, verifier: FindingVerifier) -> None:
        """compliance FAIL + risk_analysis HIGH 不是矛盾。"""
        clause = "任何一方违约的，应向对方支付合同总价百分之三十的违约金"
        dim_results = {
            "compliance": DimensionResult(
                dimension="compliance",
                compliance_results=[
                    ComplianceResult(
                        rule_id="R001",
                        rule_description="test",
                        status=ComplianceStatus.FAIL,
                        clause_text=clause,
                    ),
                ],
            ),
            "risk_analysis": DimensionResult(
                dimension="risk_analysis",
                risks=[
                    RiskFinding(
                        clause_text=clause,
                        risk_type="test",
                        severity=Severity.HIGH,
                        explanation="t",
                        suggestion="t",
                    ),
                ],
            ),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert len(stats["contradictions"]) == 0

    def test_no_contradiction_without_both_dimensions(self, verifier: FindingVerifier) -> None:
        """缺少某个维度时不应报矛盾。"""
        dim_results = {
            "risk_analysis": DimensionResult(
                dimension="risk_analysis",
                risks=[
                    RiskFinding(
                        clause_text="test clause text here",
                        risk_type="test",
                        severity=Severity.HIGH,
                        explanation="t",
                        suggestion="t",
                    ),
                ],
            ),
        }
        stats = verifier.verify_all(dim_results, FULL_TEXT)
        assert len(stats["contradictions"]) == 0


# ── _best_fuzzy_ratio ──────────────────────────────────


class TestFuzzyRatio:
    """_best_fuzzy_ratio 静态方法测试。"""

    def test_exact_substring(self) -> None:
        assert FindingVerifier._best_fuzzy_ratio("甲方", "甲方向乙方提供服务") == 1.0

    def test_empty_needle(self) -> None:
        assert FindingVerifier._best_fuzzy_ratio("", "任何文本") == 0.0

    def test_empty_haystack(self) -> None:
        assert FindingVerifier._best_fuzzy_ratio("任何文本", "") == 0.0

    def test_similar_text_above_threshold(self) -> None:
        """高度相似但非精确匹配应返回较高比率。"""
        needle = "甲方应在三十日内完成验收"
        haystack = "第二条 甲方应当在三十日内完成验收工作并出具确认书"
        ratio = FindingVerifier._best_fuzzy_ratio(needle, haystack)
        assert ratio >= 0.6

    def test_completely_different(self) -> None:
        """完全不同的文本应返回低比率。"""
        ratio = FindingVerifier._best_fuzzy_ratio(
            "知识产权归属条款",
            "本合同有效期为自签订之日起两年",
        )
        assert ratio < 0.5
