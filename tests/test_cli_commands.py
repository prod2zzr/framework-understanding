"""Tests for new CLI commands: accept-rule and audit-summary."""

import json
from pathlib import Path

import pytest
import yaml


# ── accept-rule ───────────────────────────────────────


class TestAcceptRule:
    """accept-rule 命令的核心逻辑测试。"""

    @pytest.fixture()
    def rules_file(self, tmp_path: Path) -> Path:
        """创建临时规则文件。"""
        rules = {
            "version": "1.0",
            "compliance_rules": [
                {"id": "TERM_001", "description": "合同必须明确约定合同期限", "category": "basic_terms", "severity": "high"},
            ],
        }
        path = tmp_path / "rules.yaml"
        path.write_text(yaml.dump(rules, allow_unicode=True), encoding="utf-8")
        return path

    @pytest.fixture()
    def report_with_candidates(self, tmp_path: Path) -> Path:
        """创建包含候选规则的审查报告 JSON。"""
        report = {
            "contract_name": "测试合同",
            "overall_risk_score": 65,
            "candidate_rules": [
                {
                    "id": "AUTO_违约金过高",
                    "description": "违约金比例达到合同总价30%",
                    "category": "penalty",
                    "severity": "high",
                    "source": "auto_discovered",
                    "evidence_example": "应向对方支付合同总价百分之三十的违约金",
                },
                {
                    "id": "AUTO_付款期限过长",
                    "description": "30日付款期限对甲方现金流有压力",
                    "category": "payment",
                    "severity": "medium",
                    "source": "auto_discovered",
                },
            ],
        }
        path = tmp_path / "report.json"
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        return path

    @pytest.fixture()
    def empty_report(self, tmp_path: Path) -> Path:
        """创建无候选规则的报告。"""
        report = {"contract_name": "空", "candidate_rules": []}
        path = tmp_path / "empty_report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def test_accept_all_rules(self, rules_file: Path, report_with_candidates: Path) -> None:
        """--all 应将所有候选规则写入 YAML。"""
        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "accept-rule", str(report_with_candidates),
            "--rules", str(rules_file), "--all",
        ])
        assert result.exit_code == 0
        assert "已添加" in result.output

        # 验证 YAML 内容
        with open(rules_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ids = [r["id"] for r in data["compliance_rules"]]
        assert "AUTO_违约金过高" in ids
        assert "AUTO_付款期限过长" in ids
        assert "TERM_001" in ids  # 原有规则保留
        assert len(data["compliance_rules"]) == 3

    def test_accept_specific_rule(self, rules_file: Path, report_with_candidates: Path) -> None:
        """--id 应只添加指定规则。"""
        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "accept-rule", str(report_with_candidates),
            "--rules", str(rules_file), "--id", "AUTO_违约金过高",
        ])
        assert result.exit_code == 0

        with open(rules_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ids = [r["id"] for r in data["compliance_rules"]]
        assert "AUTO_违约金过高" in ids
        assert "AUTO_付款期限过长" not in ids

    def test_skip_duplicate_rule(self, rules_file: Path, report_with_candidates: Path) -> None:
        """已存在的规则 ID 应跳过。"""
        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        # 先添加一次
        runner = CliRunner()
        runner.invoke(app, [
            "accept-rule", str(report_with_candidates),
            "--rules", str(rules_file), "--all",
        ])
        # 再添加一次
        result = runner.invoke(app, [
            "accept-rule", str(report_with_candidates),
            "--rules", str(rules_file), "--all",
        ])
        assert "跳过" in result.output

        with open(rules_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["compliance_rules"]) == 3  # 不重复添加

    def test_no_candidates(self, empty_report: Path) -> None:
        """无候选规则应正常退出。"""
        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["accept-rule", str(empty_report)])
        assert result.exit_code == 0
        assert "无候选规则" in result.output

    def test_added_date_and_source(self, rules_file: Path, report_with_candidates: Path) -> None:
        """新规则应包含 added_date 和 source 字段。"""
        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        runner.invoke(app, [
            "accept-rule", str(report_with_candidates),
            "--rules", str(rules_file), "--all",
        ])

        with open(rules_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        new_rules = [r for r in data["compliance_rules"] if r["id"].startswith("AUTO_")]
        for rule in new_rules:
            assert "added_date" in rule
            assert rule["source"] == "auto_discovered"


# ── audit-summary ─────────────────────────────────────


class TestAuditSummary:
    """audit-summary 命令测试。"""

    @pytest.fixture()
    def audit_file(self, tmp_path: Path) -> Path:
        """创建临时审计日志。"""
        entries = [
            {"contract": "合同A", "event": "review_start", "timestamp": "2026-04-05T10:00:00Z"},
            {"contract": "合同A", "event": "llm_call", "dimension": "risk_analysis",
             "detail": {"prompt_tokens": 500, "completion_tokens": 200, "cached": False}},
            {"contract": "合同A", "event": "llm_call", "dimension": "compliance",
             "detail": {"prompt_tokens": 400, "completion_tokens": 150, "cached": True}},
            {"contract": "合同A", "event": "verification_complete",
             "detail": {"evidence_verified": 3, "evidence_unverified": 1, "evidence_missing": 0, "contradictions": []}},
            {"contract": "合同A", "event": "review_complete",
             "detail": {"overall_risk_score": 55, "dimensions_succeeded": ["risk_analysis", "compliance"], "dimensions_failed": []}},
        ]
        path = tmp_path / "audit.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path

    def test_summary_output(self, audit_file: Path) -> None:
        """应输出人类可读的摘要。"""
        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["audit-summary", str(audit_file)])
        assert result.exit_code == 0
        assert "合同A" in result.output
        assert "总事件数: 5" in result.output
        assert "LLM 调用: 2" in result.output
        assert "55/100" in result.output

    def test_filter_by_contract(self, audit_file: Path, tmp_path: Path) -> None:
        """--contract 应按合同名称过滤。"""
        # 追加另一个合同的条目
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"contract": "合同B", "event": "review_start"}) + "\n")

        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["audit-summary", str(audit_file), "--contract", "合同A"])
        assert "合同A" in result.output
        assert "合同B" not in result.output

    def test_empty_audit(self, tmp_path: Path) -> None:
        """空审计日志应正常退出。"""
        path = tmp_path / "empty.jsonl"
        path.write_text("")

        from typer.testing import CliRunner
        from contract_reviewer.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["audit-summary", str(path)])
        assert result.exit_code == 0
        assert "为空" in result.output
