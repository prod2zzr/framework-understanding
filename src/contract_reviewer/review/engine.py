"""Review engine: orchestrates concurrent multi-dimension contract review."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from contract_reviewer.llm.client import LLMClient, LLMError
from contract_reviewer.models.config import Settings
from contract_reviewer.models.contract import Contract, ContractChunk
from contract_reviewer.models.progress import ProgressEvent
from contract_reviewer.models.review import (
    ComplianceResult,
    ComplianceStatus,
    DimensionResult,
    LanguageIssue,
    MissingClause,
    ReviewReport,
    RiskFinding,
    Severity,
)
from contract_reviewer.rag.prompt_builder import PromptBuilder
from contract_reviewer.rag.retriever import Retriever
from contract_reviewer.plugins.registry import get_all_plugins
from contract_reviewer.review.audit import AuditTrail
from contract_reviewer.review.dimensions import DIMENSIONS, DimensionSpec
from contract_reviewer.review.hooks import call_hooks
from contract_reviewer.review.learnings import extract_candidate_rules
from contract_reviewer.review.verifier import FindingVerifier

logger = logging.getLogger(__name__)


# Pydantic models for structured LLM output per dimension
class RiskAnalysisOutput(BaseModel):
    risks: list[RiskFinding] = []


class ComplianceOutput(BaseModel):
    results: list[ComplianceResult] = []


class CompletenessOutput(BaseModel):
    missing_clauses: list[MissingClause] = []


class FairnessOutput(BaseModel):
    risks: list[RiskFinding] = []


# Map dimension to its output model
DIMENSION_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "risk_analysis": RiskAnalysisOutput,
    "compliance": ComplianceOutput,
    "completeness": CompletenessOutput,
    "term_fairness": FairnessOutput,
}


class ReviewEngine:
    """Orchestrate concurrent multi-dimension contract review."""

    def __init__(
        self,
        llm: LLMClient,
        retriever: Retriever | None,
        prompt_builder: PromptBuilder,
        settings: Settings,
        rules: list[dict] | None = None,
        hooks: list | None = None,
    ):
        self.llm = llm
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.settings = settings
        self.rules = rules or []
        self.hooks = hooks or []
        self._semaphore = asyncio.Semaphore(settings.llm_max_concurrent)

    async def review(
        self,
        contract: Contract,
        dimensions: list[str] | None = None,
        on_progress: Callable[[ProgressEvent], Any] | None = None,
    ) -> ReviewReport:
        """Run all (or selected) review dimensions concurrently."""
        active_dims = dimensions or self.settings.review_dimensions
        system_prompt = self.prompt_builder.build_system_prompt()

        # Local audit trail — avoids race condition if review() is called concurrently
        audit = AuditTrail(contract.name)
        audit.log("review_start", detail={"dimensions": active_dims})

        # Lifecycle hooks
        await call_hooks(self.hooks, "on_review_start", contract)

        # Cache plugins once per review (not per-chunk)
        plugins = list(get_all_plugins().values())

        # Run dimensions concurrently — track which dims actually run
        run_dims: list[str] = []
        tasks = []
        for dim_name in active_dims:
            if dim_name not in DIMENSIONS:
                logger.warning("Unknown dimension: %s, skipping", dim_name)
                continue
            dim_spec = DIMENSIONS[dim_name]
            run_dims.append(dim_name)
            tasks.append(
                self._run_dimension(
                    contract, dim_spec, system_prompt, on_progress, audit, plugins
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assemble report — zip with run_dims (not active_dims) to stay aligned
        dim_results: dict[str, DimensionResult] = {}
        for dim_name, result in zip(run_dims, results):
            if isinstance(result, Exception):
                logger.error("Dimension %s failed: %s", dim_name, result)
                dim_results[dim_name] = DimensionResult(
                    dimension=dim_name, success=False, error=str(result)
                )
            else:
                dim_results[dim_name] = result

        # Independent verification stage
        verifier = FindingVerifier()
        verification_summary = verifier.verify_all(dim_results, contract.full_text)
        audit.log("verification_complete", detail=verification_summary)

        # Extract candidate rules (institutional memory)
        all_risks = [
            r for dr in dim_results.values() if dr.success for r in dr.risks
        ]
        candidate_rules = extract_candidate_rules(all_risks, self.rules)
        if candidate_rules:
            audit.log("candidate_rules", detail={
                "count": len(candidate_rules),
                "ids": [c["id"] for c in candidate_rules],
            })

        report = ReviewReport(
            contract_name=contract.name,
            dimensions=dim_results,
            overall_risk_score=self._compute_risk_score(dim_results),
            verification_summary=verification_summary,
            audit_summary=audit.summary(),
            candidate_rules=candidate_rules,
        )

        # Generate summary
        report.summary = await self._generate_summary(report, system_prompt)

        audit.log("review_complete", detail={
            "overall_risk_score": report.overall_risk_score,
            "dimensions_succeeded": [d for d, r in dim_results.items() if r.success],
            "dimensions_failed": [d for d, r in dim_results.items() if not r.success],
        })

        # Lifecycle hooks
        await call_hooks(self.hooks, "on_report_ready", report)

        # Store audit trail for callers that need to persist it
        self._last_audit_trail = audit

        return report

    async def _run_dimension(
        self,
        contract: Contract,
        dim_spec: DimensionSpec,
        system_prompt: str,
        on_progress: Callable[[ProgressEvent], Any] | None,
        audit: AuditTrail | None = None,
        plugins: list | None = None,
    ) -> DimensionResult:
        """Run a single review dimension across relevant contract chunks."""
        if audit:
            audit.log("dimension_start", dimension=dim_spec.name)
        if on_progress:
            await _call_progress(on_progress, ProgressEvent(
                dimension=dim_spec.name, status="started",
            ))

        # For completeness check, we send the full contract text
        if dim_spec.name == "completeness":
            return await self._run_completeness(contract, dim_spec, system_prompt, on_progress)

        # For other dimensions, process chunks
        chunks = contract.chunks or [
            ContractChunk(text=contract.full_text, chunk_index=0, total_chunks=1)
        ]

        all_risks: list[RiskFinding] = []
        all_compliance: list[ComplianceResult] = []

        for chunk in chunks:
            # Retrieve legal context if RAG is available
            legal_context = None
            if self.retriever:
                legal_context = await self.retriever.retrieve(
                    chunk.text, topic_filter=dim_spec.topic_filter
                )

            # Build prompt
            rules = self.rules if dim_spec.name == "compliance" else None
            user_prompt = self.prompt_builder.build_review_prompt(
                template_name=dim_spec.prompt_template,
                contract_text=chunk.text,
                legal_context=legal_context,
                rules=rules,
            )

            # Call LLM with concurrency control
            output_model = DIMENSION_OUTPUT_MODELS.get(dim_spec.name)
            async with self._semaphore:
                result = await self.llm.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=output_model,
                )

            # Parse result defensively — LLM may return malformed data
            if isinstance(result, dict):
                if dim_spec.name in ("risk_analysis", "term_fairness"):
                    for r in result.get("risks", []):
                        if isinstance(r, dict):
                            try:
                                all_risks.append(RiskFinding(**r))
                            except ValidationError as e:
                                logger.warning("Skipping malformed risk finding: %s", e)
                elif dim_spec.name == "compliance":
                    for cr in result.get("results", []):
                        if isinstance(cr, dict):
                            try:
                                all_compliance.append(ComplianceResult(**cr))
                            except ValidationError as e:
                                logger.warning("Skipping malformed compliance result: %s", e)

            # Run applicable plugins on this chunk
            for plugin in (plugins or []):
                try:
                    if plugin.applicable_to(chunk):
                        plugin_findings = await plugin.review_chunk(
                            chunk, legal_context or [], self.llm
                        )
                        all_risks.extend(plugin_findings)
                except Exception as e:
                    logger.warning("Plugin %s failed on chunk %d: %s", plugin.name, chunk.chunk_index, e)

            if on_progress:
                await _call_progress(on_progress, ProgressEvent(
                    dimension=dim_spec.name,
                    status="chunk_complete",
                    chunk_index=chunk.chunk_index,
                    total_chunks=chunk.total_chunks,
                ))

        dim_result = DimensionResult(dimension=dim_spec.name)
        if dim_spec.name in ("risk_analysis", "term_fairness"):
            dim_result.risks = all_risks
        elif dim_spec.name == "compliance":
            dim_result.compliance_results = all_compliance

        if on_progress:
            await _call_progress(on_progress, ProgressEvent(
                dimension=dim_spec.name, status="completed",
            ))

        return dim_result

    async def _run_completeness(
        self,
        contract: Contract,
        dim_spec: DimensionSpec,
        system_prompt: str,
        on_progress: Callable[[ProgressEvent], Any] | None,
    ) -> DimensionResult:
        """Completeness check uses full text, not chunks."""
        legal_context = None
        if self.retriever:
            legal_context = await self.retriever.retrieve(
                "合同完整性 必备条款 standard clauses"
            )

        user_prompt = self.prompt_builder.build_review_prompt(
            template_name=dim_spec.prompt_template,
            contract_text=contract.full_text[:8000],  # Truncate for very long contracts
            legal_context=legal_context,
        )

        async with self._semaphore:
            result = await self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CompletenessOutput,
            )

        dim_result = DimensionResult(dimension=dim_spec.name)
        if isinstance(result, dict):
            for m in result.get("missing_clauses", []):
                if isinstance(m, dict):
                    try:
                        dim_result.missing_clauses.append(MissingClause(**m))
                    except ValidationError as e:
                        logger.warning("Skipping malformed missing clause: %s", e)

        if on_progress:
            await _call_progress(on_progress, ProgressEvent(
                dimension=dim_spec.name, status="completed",
            ))

        return dim_result

    def _compute_risk_score(self, results: dict[str, DimensionResult]) -> int:
        """Compute overall risk score from dimension results."""
        severity_weights = {
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0,
        }
        total_weight = 0

        for dim_result in results.values():
            if not dim_result.success:
                continue
            for risk in dim_result.risks:
                total_weight += severity_weights.get(risk.severity, 0)
            for missing in dim_result.missing_clauses:
                total_weight += severity_weights.get(missing.importance, 0)
            for comp in dim_result.compliance_results:
                if comp.status == ComplianceStatus.FAIL:
                    total_weight += 8
                elif comp.status == ComplianceStatus.WARNING:
                    total_weight += 3

        # Normalize to 0-100
        return min(100, total_weight)

    async def _generate_summary(
        self, report: ReviewReport, system_prompt: str
    ) -> str:
        """Generate an executive summary of the review."""
        findings_summary = []
        for dim_name, dim_result in report.dimensions.items():
            if not dim_result.success:
                findings_summary.append(f"{dim_name}: 审核失败 - {dim_result.error}")
                continue
            high_risks = [r for r in dim_result.risks if r.severity == Severity.HIGH]
            fails = [c for c in dim_result.compliance_results if c.status == ComplianceStatus.FAIL]
            missing_high = [m for m in dim_result.missing_clauses if m.importance == Severity.HIGH]
            findings_summary.append(
                f"{dim_name}: {len(high_risks)} high risks, {len(fails)} compliance failures, {len(missing_high)} critical missing clauses"
            )

        prompt = (
            f"基于以下合同审核结果，生成一段简洁的中文执行摘要（3-5句话）。\n\n"
            f"合同名称: {report.contract_name}\n"
            f"风险评分: {report.overall_risk_score}/100 ({report.risk_score_label()})\n\n"
            f"各维度发现:\n" + "\n".join(findings_summary)
        )

        async with self._semaphore:
            return await self.llm.complete(system_prompt=system_prompt, user_prompt=prompt)


async def _call_progress(callback: Callable, event: ProgressEvent) -> None:
    """Call a progress callback, handling both sync and async. Never raises."""
    try:
        result = callback(event)
        if asyncio.iscoroutine(result):
            await result
    except Exception as e:
        logger.warning("Progress callback error (non-fatal): %s", e)
