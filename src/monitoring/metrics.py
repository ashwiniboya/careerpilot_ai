"""
Metrics — token usage, latency, and cost tracking for CareerPilot AI.

Tracks:
  - Prompt / completion token counts per agent call
  - Estimated cost based on Gemini pricing tiers
  - Latency per agent invocation

Persists data to the SQLite `token_usage` table via SQLAlchemy.
Also maintains in-process counters for the current process lifetime.

Usage:
    from src.monitoring.metrics import MetricsCollector
    mc = MetricsCollector(db_session=db, user_id=1)
    mc.record(agent_name="resume_agent", prompt_tokens=500, completion_tokens=300, latency_s=1.2)
    summary = mc.get_session_summary()
"""
from __future__ import annotations

import datetime
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Dict, Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Gemini pricing (USD per 1 million tokens, as of mid-2025)
# Source: https://ai.google.dev/pricing
# ---------------------------------------------------------------------------

_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "text-embedding-004": {"input": 0.025, "output": 0.0},
}
_DEFAULT_PRICING = {"input": 1.0, "output": 3.0}  # Conservative fallback


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Compute estimated USD cost for a single API call."""
    pricing = _PRICING.get(model, _DEFAULT_PRICING)
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 8)


# ---------------------------------------------------------------------------
# In-process counters (cleared on restart)
# ---------------------------------------------------------------------------

class _ProcessCounters:
    def __init__(self):
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.call_count: int = 0
        self.by_agent: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "total_latency_s": 0.0}
        )

    def record(self, agent_name: str, prompt_tokens: int, completion_tokens: int, cost: float, latency_s: float):
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost_usd += cost
        self.call_count += 1
        rec = self.by_agent[agent_name]
        rec["calls"] += 1
        rec["prompt_tokens"] += prompt_tokens
        rec["completion_tokens"] += completion_tokens
        rec["cost_usd"] += cost
        rec["total_latency_s"] += latency_s


_counters = _ProcessCounters()


# ---------------------------------------------------------------------------
# MetricsCollector — the public interface used by agents / API layer
# ---------------------------------------------------------------------------

class MetricsCollector:
    """
    Records agent call metrics both in-process and to SQLite.

    Args:
        db_session: SQLAlchemy session. If None, only in-process counters are updated.
        user_id:    The authenticated user ID (for per-user cost attribution).
    """

    def __init__(self, db_session=None, user_id: Optional[int] = None):
        self._db = db_session
        self._user_id = user_id

    def record(
        self,
        agent_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_s: float = 0.0,
        model: str = "gemini-2.5-flash",
    ) -> float:
        """
        Record a single agent invocation.

        Returns:
            Estimated cost in USD for this call.
        """
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)
        _counters.record(agent_name, prompt_tokens, completion_tokens, cost, latency_s)

        # Persist to database if session available
        if self._db is not None:
            try:
                from database.models import TokenUsage
                record = TokenUsage(
                    user_id=self._user_id,
                    agent_name=agent_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost=cost,
                    timestamp=datetime.datetime.utcnow(),
                )
                self._db.add(record)
                self._db.commit()
            except Exception as e:
                logger.warning(f"[MetricsCollector] Failed to persist metrics: {e}")

        logger.debug(
            f"[metrics] {agent_name}: {prompt_tokens}pt + {completion_tokens}ct "
            f"= ${cost:.6f} | {latency_s:.2f}s"
        )
        return cost

    @contextmanager
    def timed_call(self, agent_name: str, model: str = "gemini-2.5-flash"):
        """
        Context manager that auto-measures latency.

        Usage:
            with mc.timed_call("resume_agent") as timer:
                response = agent.run(prompt)
            timer.record(prompt_tokens=..., completion_tokens=...)
        """
        start = time.perf_counter()
        timer = _TimerHandle(self, agent_name, model, start)
        yield timer
        # If record() was not called manually, we record with 0 tokens
        if not timer.recorded:
            timer.record()

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def get_session_summary(self) -> Dict[str, Any]:
        """Return in-process aggregate metrics."""
        return {
            "total_calls": _counters.call_count,
            "total_prompt_tokens": _counters.total_prompt_tokens,
            "total_completion_tokens": _counters.total_completion_tokens,
            "total_cost_usd": round(_counters.total_cost_usd, 6),
            "by_agent": dict(_counters.by_agent),
        }

    def get_user_cost_history(self, limit: int = 20) -> list:
        """Fetch recent token_usage rows for the current user from SQLite."""
        if self._db is None or self._user_id is None:
            return []
        try:
            from database.models import TokenUsage
            rows = (
                self._db.query(TokenUsage)
                .filter(TokenUsage.user_id == self._user_id)
                .order_by(TokenUsage.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "agent": r.agent_name,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "cost_usd": r.cost,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"[MetricsCollector] Could not fetch history: {e}")
            return []


class _TimerHandle:
    """Internal helper returned by MetricsCollector.timed_call()."""

    def __init__(self, collector: MetricsCollector, agent_name: str, model: str, start: float):
        self._collector = collector
        self._agent_name = agent_name
        self._model = model
        self._start = start
        self.recorded = False
        self.latency_s = 0.0

    def record(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> float:
        self.latency_s = time.perf_counter() - self._start
        self.recorded = True
        return self._collector.record(
            agent_name=self._agent_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_s=self.latency_s,
            model=self._model,
        )
