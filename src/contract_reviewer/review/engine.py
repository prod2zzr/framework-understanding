"""Review engine: orchestrates concurrent multi-dimension contract review."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from contract_reviewer.llm.client import LLMClient
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
from contract_reviewer.review.dimensions import DIMENSIONS, DimensionSpec

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
    ):
        self.llm = llm
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.settings = settings
        self.rules = rules or []
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

        # Run dimensions concurrently
        tasks = []
        for dim_name in active_dims:
            if dim_name not in DIMENSIONS:
                logger.warning("Unknown dimension: %s, skipping", dim_name)
                continue
            dim_spec = DIMENSIONS[dim_name]
            tasks.append(
                self._run_dimension(
                    contract, dim_spec, system_prompt, on_progress
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assemble report
        dim_results: dict[str, DimensionResult] = {}
        for dim_name, result in zip(active_dims, results):
            if isinstance(result, Exception):
                logger.error("Dimension %s failed: %s", dim_name, result)
                dim_results[dim_name] = DimensionResult(
                    dimension=dim_name, success=False, error=str(result)
                )
            else:
                dim_results[dim_name] = result

        report = ReviewReport(
            contract_name=contract.name,
            dimensions=dim_results,
            overall_risk_score=self._compute_risk_score(dim_results),
        )

        # Generate summary
        report.summary = await self._generate_summary(report, system_prompt)

        return report

    async def _run_dimension(
        self,
        contract: Contract,
        dim_spec: DimensionSpec,
        system_prompt: str,
        on_progress: Callable[[ProgressEvent], Any] | None,
    ) -> DimensionResult:
        """Run a single review dimension across relevant contract chunks."""
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

            # Parse result
            if isinstance(result, dict):
                if dim_spec.name in ("risk_analysis", "term_fairness"):
                    risks = result.get("risks", [])
                    for r in risks:
                        if isinstance(r, dict):
                            all_risks.append(RiskFinding(**r))
                elif dim_spec.name == "compliance":
                    comp_results = result.get("results", [])
                    for cr in comp_results:
                        if isinstance(cr, dict):
                            all_compliance.append(ComplianceResult(**cr))

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
            missing = result.get("missing_clauses", [])
            for m in missing:
                if isinstance(m, dict):
                    dim_result.missing_clauses.append(MissingClause(**m))

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
    """Call a progress callback, handling both sync and async."""
    result = callback(event)
    if asyncio.iscoroutine(result):
        await result
