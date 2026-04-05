"""Assemble prompts from templates, contract chunks, and RAG context."""

import logging
from pathlib import Path

import tiktoken
from jinja2 import Environment, FileSystemLoader

from contract_reviewer.rag.retriever import RetrievedContext

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Build prompts from Jinja2 templates with token budget awareness."""

    def __init__(self, prompts_dir: str, max_context_tokens: int = 4096):
        self.env = Environment(
            loader=FileSystemLoader(prompts_dir),
            keep_trailing_newline=True,
        )
        self.max_context_tokens = max_context_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")

    def build_system_prompt(self) -> str:
        """Load and render the shared system prompt."""
        template = self.env.get_template("system.jinja2")
        return template.render()

    def build_review_prompt(
        self,
        template_name: str,
        contract_text: str,
        legal_context: list[RetrievedContext] | None = None,
        rules: list[dict] | None = None,
        **extra_vars: object,
    ) -> str:
        """Build a review dimension prompt with contract text and RAG context.

        Token budget allocation:
        - Contract text: always included in full (caller should pre-chunk)
        - Legal context: filled in relevance order until budget is reached
        - Rules: always included if provided
        """
        template = self.env.get_template(template_name)

        # Format legal context within token budget
        context_text = ""
        if legal_context:
            context_text = self._fit_context(
                legal_context, contract_text, rules
            )

        rules_text = ""
        if rules:
            rules_text = self._format_rules(rules)

        rendered = template.render(
            contract_text=contract_text,
            legal_context=context_text,
            rules=rules_text,
            **extra_vars,
        )

        # Pre-flight check: validate token budget and auto-trim if needed
        rendered_tokens = len(self._enc.encode(rendered))
        if rendered_tokens > self.max_context_tokens:
            overflow = rendered_tokens - self.max_context_tokens
            logger.warning(
                "Prompt exceeds token budget by %d tokens (%d > %d, template=%s). "
                "Trimming legal context.",
                overflow,
                rendered_tokens,
                self.max_context_tokens,
                template_name,
            )
            # 重新渲染：缩减法律上下文的可用空间
            if legal_context:
                trimmed_context = self._fit_context(
                    legal_context, contract_text, rules,
                    extra_reduction=overflow + 100,
                )
                rendered = template.render(
                    contract_text=contract_text,
                    legal_context=trimmed_context,
                    rules=rules_text,
                    **extra_vars,
                )
                final_tokens = len(self._enc.encode(rendered))
                logger.info(
                    "Prompt trimmed: %d → %d tokens (template=%s)",
                    rendered_tokens, final_tokens, template_name,
                )

        return rendered

    def _fit_context(
        self,
        contexts: list[RetrievedContext],
        contract_text: str,
        rules: list[dict] | None,
        extra_reduction: int = 0,
    ) -> str:
        """Fit legal context within available token budget."""
        # Calculate tokens used by other components
        contract_tokens = len(self._enc.encode(contract_text))
        rules_tokens = len(self._enc.encode(str(rules))) if rules else 0
        overhead = 200  # Template structure, instructions
        available = self.max_context_tokens - contract_tokens - rules_tokens - overhead - extra_reduction

        if available <= 0:
            return ""

        # Add contexts in relevance order
        pieces: list[str] = []
        used = 0
        for ctx in sorted(contexts, key=lambda c: c.relevance_score, reverse=True):
            entry = f"【{ctx.source} {ctx.article_number}】{ctx.text}"
            entry_tokens = len(self._enc.encode(entry))
            if used + entry_tokens > available:
                break  # Don't truncate individual entries
            pieces.append(entry)
            used += entry_tokens

        return "\n\n".join(pieces)

    @staticmethod
    def _format_rules(rules: list[dict]) -> str:
        """Format compliance rules for prompt injection."""
        lines = []
        for r in rules:
            severity = r.get("severity", "medium").upper()
            desc = r.get("description", r.get("description_en", ""))
            lines.append(f"[{severity}] {r.get('id', '')}: {desc}")
        return "\n".join(lines)
