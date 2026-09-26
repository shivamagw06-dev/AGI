"""Provider protocol — every knowledge source implements this."""

from __future__ import annotations

import time
from typing import Any, Optional, Protocol

from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class KnowledgeProvider(Protocol):
    spec: ProviderSpec

    def health_check(self) -> str:
        """Return ok | degraded | empty | error."""
        ...

    def consult(self, plan: QueryPlan) -> ProviderResult:
        ...


def timed_result(
    provider_id: str,
    *,
    ok: bool,
    empty: bool,
    confidence: float,
    t0: float,
    summary: str = "",
    why: Optional[list[str]] = None,
    evidence: Optional[list[dict[str, Any]]] = None,
    facts: Optional[list[dict[str, Any]]] = None,
    raw: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
    rejected_reason: Optional[str] = None,
) -> ProviderResult:
    return ProviderResult(
        provider_id=provider_id,
        ok=ok,
        empty=empty,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        confidence=confidence,
        summary=summary or "",
        why=list(why or []),
        evidence=list(evidence or []),
        facts=list(facts or []),
        raw=dict(raw or {}),
        error=error,
        rejected_reason=rejected_reason,
    )


def empty_result(provider_id: str, t0: float, reason: str = "empty") -> ProviderResult:
    return timed_result(
        provider_id,
        ok=True,
        empty=True,
        confidence=0.0,
        t0=t0,
        rejected_reason=reason,
    )


def error_result(provider_id: str, t0: float, exc: Exception) -> ProviderResult:
    return timed_result(
        provider_id,
        ok=False,
        empty=True,
        confidence=0.0,
        t0=t0,
        error=f"{type(exc).__name__}:{str(exc)[:200]}",
        rejected_reason="error",
    )
