"""LLM cost tracker — monitors token usage and spending per pipeline run.

Tracks cumulative token usage across all LLM calls in a pipeline run
and raises alerts when approaching budget limits.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.interfaces.llm_provider import LLMResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Approximate pricing per 1K tokens (USD) by provider + model
COST_TABLE: dict[str, dict[str, dict[str, float]]] = {
    "gemini": {
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
    },
    "openai": {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    },
    "claude": {
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    },
    "groq": {
        "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},
    },
}


@dataclass
class UsageEntry:
    """Single LLM usage entry."""

    module_name: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass
class CostTracker:
    """Tracks LLM token usage and cost for a single pipeline run.

    Attributes:
        run_id: UUID of the pipeline run being tracked.
        max_cost_usd: Maximum allowed cost for this run (0 = unlimited).
        entries: List of individual usage entries.
    """

    run_id: uuid.UUID
    max_cost_usd: float = 0.0
    entries: list[UsageEntry] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        """Total accumulated cost in USD."""
        return sum(e.cost_usd for e in self.entries)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed across all entries."""
        return sum(e.total_tokens for e in self.entries)

    @property
    def total_prompt_tokens(self) -> int:
        """Total prompt/input tokens consumed."""
        return sum(e.prompt_tokens for e in self.entries)

    @property
    def total_completion_tokens(self) -> int:
        """Total completion/output tokens consumed."""
        return sum(e.completion_tokens for e in self.entries)

    def estimate_cost(
        self, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Estimate USD cost for a set of tokens.

        Args:
            provider: Provider name (gemini, openai, etc.).
            model: Model identifier.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        pricing = COST_TABLE.get(provider, {}).get(
            model, {"input": 0.005, "output": 0.005}
        )
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def record(self, module_name: str, response: LLMResponse) -> UsageEntry:
        """Record an LLM response's usage.

        Args:
            module_name: Pipeline module that made the LLM call.
            response: LLMResponse from the provider.

        Returns:
            The recorded UsageEntry.

        Raises:
            RuntimeError: If recording would exceed the cost budget.
        """
        cost = self.estimate_cost(
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )

        entry = UsageEntry(
            module_name=module_name,
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            cost_usd=cost,
        )
        self.entries.append(entry)

        logger.info(
            "llm usage recorded",
            run_id=str(self.run_id),
            module=module_name,
            provider=response.provider,
            model=response.model,
            tokens=response.total_tokens,
            cost_usd=f"${cost:.6f}",
            total_run_cost=f"${self.total_cost:.6f}",
        )

        # Budget warning at 80%
        if self.max_cost_usd > 0:
            usage_pct = self.total_cost / self.max_cost_usd
            if usage_pct >= 1.0:
                logger.error(
                    "llm cost budget exceeded",
                    run_id=str(self.run_id),
                    total_cost=f"${self.total_cost:.6f}",
                    budget=f"${self.max_cost_usd:.2f}",
                )
                raise RuntimeError(
                    f"LLM cost budget exceeded: ${self.total_cost:.4f} > "
                    f"${self.max_cost_usd:.2f}"
                )
            elif usage_pct >= 0.8:
                logger.warning(
                    "llm cost approaching budget limit",
                    run_id=str(self.run_id),
                    total_cost=f"${self.total_cost:.6f}",
                    budget=f"${self.max_cost_usd:.2f}",
                    usage_pct=f"{usage_pct:.0%}",
                )

        return entry

    def get_summary(self) -> dict:
        """Get a summary of all usage in this run.

        Returns:
            Dict with total tokens, cost, and per-module breakdown.
        """
        by_module: dict[str, dict] = {}
        for entry in self.entries:
            if entry.module_name not in by_module:
                by_module[entry.module_name] = {
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "calls": 0,
                }
            by_module[entry.module_name]["tokens"] += entry.total_tokens
            by_module[entry.module_name]["cost_usd"] += entry.cost_usd
            by_module[entry.module_name]["calls"] += 1

        return {
            "run_id": str(self.run_id),
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "budget_usd": self.max_cost_usd,
            "by_module": by_module,
        }
