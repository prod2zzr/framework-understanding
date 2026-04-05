"""Tests for aggregator — dedup, text similarity, markdown report formatting."""

from datetime import datetime

from contract_reviewer.models.review import (
    ComplianceResult,
    ComplianceStatus,
    DimensionResult,
    MissingClause,
    ReviewReport,
    RiskFinding,
    Severity,
)
from contract_reviewer.review.aggregator import (
    _cn_num,
    _text_similarity,
    deduplicate_risks,
    format_report_markdown,
)


# ── 去重 ──────────────────────────────────────────────


class TestDeduplicate:
    """deduplicate_risks 测试。"""

    def test_empty_list(self) -> None:
        assert deduplicate_risks([]) == []

    def test_no_duplicates(self, risk_high: RiskFinding, risk_low: RiskFinding) -> None:
        """不相似的 findings 应全部保留。"""
        result = deduplicate_risks([risk_high, risk_low])
        assert len(result) == 2

    def test_exact_duplicate_removed(self, risk_high: RiskFinding) -> None:
        """完全相同的 clause_text 应去重。"""
        dup = risk_high.model_copy()
        result = deduplicate_risks([risk_high, dup])
        assert len(result) == 1

    def test_substring_duplicate_removed(self) -> None:
        """短文本是长文本的子串时应视为重复。"""
        r1 = RiskFinding(
            clause_text="甲方应在三十日内支付全部款项",
            risk_type="a", severity=Severity.HIGH, explanation="e", suggestion="s",
        )
        r2 = RiskFinding(
            clause_text="甲方应在三十日内支付全部款项，逾期需支付滞纳金",
            risk_type="b", severity=Severity.MEDIUM, explanation="e", suggestion="s",
        )
        # r1 是 r2 的子串 → similarity = 1.0 > 0.85
        result = deduplicate_risks([r1, r2])
        assert len(result) == 1

    def test_similar_but_below_threshold(self) -> None:
        """相似度低于阈值的应保留。"""
        r1 = RiskFinding(
            clause_text="甲方应承担违约责任", risk_type="a",
            severity=Severity.LOW, explanation="e", suggestion="s",
        )
        r2 = RiskFinding(
            clause_text="乙方享有知识产权", risk_type="b",
            severity=Severity.LOW, explanation="e", suggestion="s",
        )
        result = deduplicate_risks([r1, r2])
        assert len(result) == 2

    def test_custom_threshold(self) -> None:
        """可自定义阈值。"""
        r1 = RiskFinding(
            clause_text="甲方应在三十日内完成验收工作",
            risk_type="a", severity=Severity.LOW, explanation="e", suggestion="s",
        )
        r2 = RiskFinding(
            clause_text="甲方应在二十日内完成验收工作",
            risk_type="b", severity=Severity.LOW, explanation="e", suggestion="s",
        )
        # 高阈值下保留
        result_high = deduplicate_risks([r1, r2], threshold=0.99)
        assert len(result_high) == 2
        # 低阈值下去重
        result_low = deduplicate_risks([r1, r2], threshold=0.5)
        assert len(result_low) == 1


# ── 文本相似度 ────────────────────────────────────────


class TestTextSimilarity:

    def test_empty_strings(self) -> None:
        assert _text_similarity("", "") == 0.0
        assert _text_similarity("abc", "") == 0.0
        assert _text_similarity("", "abc") == 0.0

    def test_identical(self) -> None:
        assert _text_similarity("相同文本", "相同文本") == 1.0

    def test_substring_containment(self) -> None:
        assert _text_similarity("短", "包含短文本") == 1.0

    def test_partial_overlap(self) -> None:
        ratio = _text_similarity("甲方应付款", "乙方应付款")
        assert 0.0 < ratio < 1.0


# ── Markdown 报告 ─────────────────────────────────────


class TestFormatReportMarkdown:

    def _make_report(self, **kwargs) -> ReviewReport:
        defaults = {
            "contract_name": "测试合同",
            "review_timestamp": datetime(2026, 4, 5, 10, 0),
            "overall_risk_score": 65,
            "summary": "合同存在中等风险",
            "dimensions": {},
        }
        defaults.update(kwargs)
        return ReviewReport(**defaults)

    def test_header_contains_essentials(self) -> None:
        report = self._make_report()
        md = format_report_markdown(report)
        assert "合同审查报告" in md
        assert "测试合同" in md
        assert "65/100" in md
        assert "中等风险" in md

    def test_risk_grouping_by_severity(self) -> None:
        """风险应按严重度分组。"""
        dim = DimensionResult(
            dimension="risk_analysis",
            risks=[
                RiskFinding(clause_text="c1", risk_type="高", severity=Severity.HIGH, explanation="e", suggestion="s"),
                RiskFinding(clause_text="c2", risk_type="低", severity=Severity.LOW, explanation="e", suggestion="s"),
            ],
        )
        report = self._make_report(dimensions={"risk_analysis": dim})
        md = format_report_markdown(report)
        assert "高风险" in md
        assert "低风险" in md

    def test_failed_dimension_shows_error(self) -> None:
        dim = DimensionResult(dimension="completeness", success=False, error="超时")
        report = self._make_report(dimensions={"completeness": dim})
        md = format_report_markdown(report)
        assert "审核失败" in md
        assert "超时" in md

    def test_compliance_table(self) -> None:
        dim = DimensionResult(
            dimension="compliance",
            compliance_results=[
                ComplianceResult(rule_id="R001", rule_description="违约对等", status=ComplianceStatus.PASS),
                ComplianceResult(rule_id="R002", rule_description="期限合理", status=ComplianceStatus.FAIL, finding="不合理"),
            ],
        )
        report = self._make_report(dimensions={"compliance": dim})
        md = format_report_markdown(report)
        assert "R001" in md
        assert "R002" in md
        assert "✅" in md
        assert "❌" in md

    def test_missing_clauses_section(self) -> None:
        dim = DimensionResult(
            dimension="completeness",
            missing_clauses=[
                MissingClause(clause_type="争议解决", importance=Severity.HIGH, description="缺少", suggestion="建议添加"),
            ],
        )
        report = self._make_report(dimensions={"completeness": dim})
        md = format_report_markdown(report)
        assert "争议解决" in md

    def test_candidate_rules_section(self) -> None:
        report = self._make_report(
            candidate_rules=[{"id": "AUTO_001", "severity": "high", "description": "新发现的风险"}],
        )
        md = format_report_markdown(report)
        assert "候选新规则" in md
        assert "AUTO_001" in md

    def test_verification_summary(self) -> None:
        report = self._make_report(
            verification_summary={
                "evidence_verified": 5,
                "evidence_unverified": 1,
                "evidence_missing": 0,
                "contradictions": ["矛盾: compliance vs risk"],
            },
        )
        md = format_report_markdown(report)
        assert "验证摘要" in md
        assert "证据已验证: 5" in md
        assert "矛盾" in md


# ── 中文数字 ──────────────────────────────────────────


class TestCnNum:
    def test_basic(self) -> None:
        assert _cn_num(1) == "一"
        assert _cn_num(10) == "十"

    def test_out_of_range(self) -> None:
        assert _cn_num(11) == "11"

    def test_zero(self) -> None:
        assert _cn_num(0) == "零"
