"""Tests for Pydantic data models — validation, defaults, enums."""

import pytest
from pydantic import ValidationError

from contract_reviewer.models.contract import Contract, ContractChunk, Section
from contract_reviewer.models.review import (
    ComplianceStatus,
    DimensionResult,
    ReviewReport,
    RiskFinding,
    Severity,
)


# ── Severity / ComplianceStatus 枚举 ─────────────────


class TestEnums:

    def test_severity_values(self) -> None:
        assert Severity.HIGH.value == "high"
        assert Severity.INFO.value == "info"

    def test_compliance_status_values(self) -> None:
        assert ComplianceStatus.PASS.value == "pass"
        assert ComplianceStatus.NOT_APPLICABLE.value == "not_applicable"


# ── RiskFinding ───────────────────────────────────────


class TestRiskFinding:

    def test_defaults(self) -> None:
        rf = RiskFinding(
            clause_text="c", risk_type="t",
            severity=Severity.LOW, explanation="e", suggestion="s",
        )
        assert rf.evidence_verified is False
        assert rf.confidence == 1.0

    def test_confidence_bounds(self) -> None:
        """confidence 应在 [0, 1] 范围内。"""
        with pytest.raises(ValidationError):
            RiskFinding(
                clause_text="c", risk_type="t",
                severity=Severity.LOW, explanation="e", suggestion="s",
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            RiskFinding(
                clause_text="c", risk_type="t",
                severity=Severity.LOW, explanation="e", suggestion="s",
                confidence=-0.1,
            )

    def test_confidence_edge_values(self) -> None:
        """边界值 0.0 和 1.0 应合法。"""
        rf0 = RiskFinding(
            clause_text="c", risk_type="t",
            severity=Severity.LOW, explanation="e", suggestion="s",
            confidence=0.0,
        )
        rf1 = RiskFinding(
            clause_text="c", risk_type="t",
            severity=Severity.LOW, explanation="e", suggestion="s",
            confidence=1.0,
        )
        assert rf0.confidence == 0.0
        assert rf1.confidence == 1.0


# ── ReviewReport ──────────────────────────────────────


class TestReviewReport:

    def test_risk_score_label_high(self) -> None:
        report = ReviewReport(contract_name="t", overall_risk_score=85)
        assert report.risk_score_label() == "高风险"

    def test_risk_score_label_medium(self) -> None:
        report = ReviewReport(contract_name="t", overall_risk_score=55)
        assert report.risk_score_label() == "中等风险"

    def test_risk_score_label_low(self) -> None:
        report = ReviewReport(contract_name="t", overall_risk_score=20)
        assert report.risk_score_label() == "低风险"

    def test_risk_score_boundary_70(self) -> None:
        """70 分应为高风险。"""
        report = ReviewReport(contract_name="t", overall_risk_score=70)
        assert report.risk_score_label() == "高风险"

    def test_risk_score_boundary_40(self) -> None:
        """40 分应为中等风险。"""
        report = ReviewReport(contract_name="t", overall_risk_score=40)
        assert report.risk_score_label() == "中等风险"

    def test_risk_score_boundary_39(self) -> None:
        """39 分应为低风险。"""
        report = ReviewReport(contract_name="t", overall_risk_score=39)
        assert report.risk_score_label() == "低风险"

    def test_risk_score_out_of_range(self) -> None:
        """分数超出 0-100 应验证失败。"""
        with pytest.raises(ValidationError):
            ReviewReport(contract_name="t", overall_risk_score=101)
        with pytest.raises(ValidationError):
            ReviewReport(contract_name="t", overall_risk_score=-1)

    def test_default_factories(self) -> None:
        report = ReviewReport(contract_name="t", overall_risk_score=0)
        assert report.dimensions == {}
        assert report.candidate_rules == []
        assert report.verification_summary == {}

    def test_timestamp_auto_generated(self) -> None:
        report = ReviewReport(contract_name="t", overall_risk_score=0)
        assert report.review_timestamp is not None


# ── DimensionResult ───────────────────────────────────


class TestDimensionResult:

    def test_default_success(self) -> None:
        dr = DimensionResult(dimension="risk_analysis")
        assert dr.success is True
        assert dr.risks == []
        assert dr.error is None

    def test_failed_dimension(self) -> None:
        dr = DimensionResult(dimension="completeness", success=False, error="timeout")
        assert dr.success is False
        assert dr.error == "timeout"


# ── Contract 模型 ─────────────────────────────────────


class TestContractModels:

    def test_section_defaults(self) -> None:
        s = Section(heading="标题", body="正文")
        assert s.section_type == "body"
        assert s.index == 0

    def test_chunk_metadata_default(self) -> None:
        c = ContractChunk(text="文本", chunk_index=0, total_chunks=1)
        assert c.metadata == {}

    def test_contract_empty_sections(self) -> None:
        c = Contract(name="空", source_path="/tmp/empty", full_text="")
        assert c.sections == []
        assert c.chunks == []
