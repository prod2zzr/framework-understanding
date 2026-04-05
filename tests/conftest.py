"""Shared test fixtures for contract_reviewer tests."""

import pytest

from contract_reviewer.models.contract import Contract, ContractChunk, Section
from contract_reviewer.models.review import (
    ComplianceResult,
    ComplianceStatus,
    DimensionResult,
    RiskFinding,
    Severity,
)


# ── 合同相关 ──────────────────────────────────────────────


@pytest.fixture()
def sample_sections() -> list[Section]:
    """典型中文合同的三个条款。"""
    return [
        Section(heading="第一条 合同标的", body="甲方向乙方提供软件开发服务。", section_type="body", index=0),
        Section(heading="第二条 价款与支付", body="合同总价为人民币壹佰万元整（¥1,000,000）。乙方应在收到甲方验收确认后三十日内支付全部款项。", section_type="body", index=1),
        Section(heading="第三条 违约责任", body="任何一方违约的，应向对方支付合同总价百分之三十的违约金。因甲方原因导致项目延期的，甲方应承担由此产生的全部损失。", section_type="body", index=2),
    ]


@pytest.fixture()
def sample_contract(sample_sections: list[Section]) -> Contract:
    """包含三个条款的示例合同。"""
    full_text = "\n".join(f"{s.heading}\n{s.body}" for s in sample_sections)
    return Contract(
        name="测试合同.pdf",
        source_path="/tmp/测试合同.pdf",
        full_text=full_text,
        sections=sample_sections,
    )


@pytest.fixture()
def long_section_contract() -> Contract:
    """包含一个超长条款的合同（用于测试分块）。"""
    long_body = "本条款包含大量细节。\n\n" + "\n\n".join(
        f"第{i}款：甲方应当在第{i}个工作日内完成第{i}项交付物的验收工作，"
        f"并在验收合格后五个工作日内出具书面验收确认书。"
        for i in range(1, 60)
    )
    sections = [Section(heading="第一条 详细条款", body=long_body, section_type="body", index=0)]
    full_text = f"{sections[0].heading}\n{sections[0].body}"
    return Contract(
        name="长合同.pdf",
        source_path="/tmp/长合同.pdf",
        full_text=full_text,
        sections=sections,
    )


# ── 审查结果相关 ──────────────────────────────────────────


@pytest.fixture()
def risk_high() -> RiskFinding:
    return RiskFinding(
        clause_text="任何一方违约的，应向对方支付合同总价百分之三十的违约金",
        risk_type="违约金过高",
        severity=Severity.HIGH,
        explanation="违约金比例达到合同总价30%，可能被认定为过高",
        suggestion="建议将违约金比例调整为合同总价的10%-20%",
    )


@pytest.fixture()
def risk_medium() -> RiskFinding:
    return RiskFinding(
        clause_text="乙方应在收到甲方验收确认后三十日内支付全部款项",
        risk_type="付款期限过长",
        severity=Severity.MEDIUM,
        explanation="30日付款期限对甲方现金流有一定压力",
        suggestion="建议缩短至15日",
    )


@pytest.fixture()
def risk_low() -> RiskFinding:
    return RiskFinding(
        clause_text="甲方向乙方提供软件开发服务",
        risk_type="标的描述模糊",
        severity=Severity.LOW,
        explanation="软件开发服务的具体范围未明确",
        suggestion="建议补充具体交付物清单",
    )


@pytest.fixture()
def dim_result_risk(risk_high: RiskFinding, risk_medium: RiskFinding) -> DimensionResult:
    return DimensionResult(
        dimension="risk_analysis",
        success=True,
        risks=[risk_high, risk_medium],
    )


@pytest.fixture()
def dim_result_compliance() -> DimensionResult:
    return DimensionResult(
        dimension="compliance",
        success=True,
        compliance_results=[
            ComplianceResult(
                rule_id="LIABILITY_001",
                rule_description="违约责任应当对等",
                status=ComplianceStatus.PASS,
                clause_text="任何一方违约的，应向对方支付合同总价百分之三十的违约金",
            ),
        ],
    )


@pytest.fixture()
def dim_result_failed() -> DimensionResult:
    return DimensionResult(
        dimension="completeness",
        success=False,
        error="LLM 调用超时",
    )
