"""Aggregate and deduplicate review results."""

from contract_reviewer.models.review import DimensionResult, ReviewReport, RiskFinding


def deduplicate_risks(risks: list[RiskFinding], threshold: float = 0.8) -> list[RiskFinding]:
    """Remove duplicate risk findings based on clause text similarity."""
    if not risks:
        return []

    unique: list[RiskFinding] = []
    seen_texts: list[str] = []

    for risk in risks:
        is_dup = False
        for seen in seen_texts:
            if _text_overlap(risk.clause_text, seen) > threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(risk)
            seen_texts.append(risk.clause_text)

    return unique


def _text_overlap(a: str, b: str) -> float:
    """Simple character-level overlap ratio."""
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if shorter in longer:
        return 1.0
    # Use character set overlap as a quick heuristic
    set_a, set_b = set(a), set(b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def format_report_markdown(report: ReviewReport) -> str:
    """Format a ReviewReport as human-readable Markdown."""
    lines = [
        f"# 合同审查报告\n",
        f"**合同**: {report.contract_name}",
        f"**审查时间**: {report.review_timestamp.strftime('%Y-%m-%d %H:%M')}",
        f"**整体风险评分**: {report.overall_risk_score}/100 ({report.risk_score_label()})\n",
    ]

    if report.summary:
        lines.append(f"## 摘要\n{report.summary}\n")

    dim_names_zh = {
        "risk_analysis": "风险分析",
        "compliance": "合规性检查",
        "completeness": "完整性检查",
        "term_fairness": "条款公平性",
    }

    section_num = 1
    for dim_name, dim_result in report.dimensions.items():
        dim_zh = dim_names_zh.get(dim_name, dim_name)
        lines.append(f"## {_cn_num(section_num)}、{dim_zh}\n")
        section_num += 1

        if not dim_result.success:
            lines.append(f"> 审核失败: {dim_result.error}\n")
            continue

        # Risks
        if dim_result.risks:
            for severity_label, emoji in [("high", "🔴 高风险"), ("medium", "🟡 中风险"), ("low", "🟢 低风险")]:
                filtered = [r for r in dim_result.risks if r.severity.value == severity_label]
                if not filtered:
                    continue
                lines.append(f"### {emoji} ({len(filtered)}项)\n")
                for i, risk in enumerate(filtered, 1):
                    lines.append(f"**{i}. {risk.risk_type}**")
                    lines.append(f"> {risk.clause_text}\n")
                    lines.append(f"**分析**: {risk.explanation}")
                    lines.append(f"**建议**: {risk.suggestion}\n")

        # Compliance
        if dim_result.compliance_results:
            lines.append("| 规则 | 状态 | 发现 |")
            lines.append("|------|------|------|")
            for cr in dim_result.compliance_results:
                status_emoji = {
                    "pass": "✅", "fail": "❌", "warning": "⚠️", "not_applicable": "➖"
                }.get(cr.status.value, "")
                lines.append(
                    f"| {cr.rule_id}: {cr.rule_description} | {status_emoji} {cr.status.value} | {cr.finding} |"
                )
            lines.append("")

        # Missing clauses
        if dim_result.missing_clauses:
            for m in dim_result.missing_clauses:
                imp_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(m.importance.value, "")
                lines.append(f"- {imp_emoji} **{m.clause_type}**: {m.description}")
                lines.append(f"  建议: {m.suggestion}")
            lines.append("")

        # Language issues
        if dim_result.language_issues:
            for li in dim_result.language_issues:
                lines.append(f"- **{li.issue_type}**: {li.text}")
                lines.append(f"  {li.explanation} → {li.suggestion}")
            lines.append("")

    return "\n".join(lines)


def _cn_num(n: int) -> str:
    """Convert small integer to Chinese numeral."""
    cn = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    return cn[n] if n < len(cn) else str(n)
