"""Production facade for Phase 3.3 Portfolio Intelligence foundation.

Ask soft-slice remains blocked until Acceptance = 100% and ASK_WIRED flips.
Does not replace the legacy PIO soft layer at portfolio_intelligence.production.
"""

from __future__ import annotations

from typing import Any, Optional

from portfolio_intelligence.foundation.catalog import get_portfolio, list_portfolio_ids
from portfolio_intelligence.foundation.orchestrator import analyse as _analyse
from portfolio_intelligence.foundation.schema import (
    ASK_WIRED,
    ASK_WIRED_VIA,
    PI_VERSION,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
)


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "module": "portfolio_intelligence_foundation",
        "programme": PROGRAMME,
        "phase": "3.3",
        "version": PI_VERSION,
        "spec": SPEC,
        "ask_wired": ASK_WIRED,
        "ask_wired_via": ASK_WIRED_VIA if ASK_WIRED else None,
        "ask_wired_policy": "kul_provider_only_after_acceptance_100",
        "uses_llm": False,
        "fabricated": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "depends_on": [
            "AGI Core v1.1 (extend, do not modify)",
            "Investment Intelligence 3.2",
            "Industry Intelligence 3.1",
        ],
        "portfolio_count": len(list_portfolio_ids()),
        "portfolios": list_portfolio_ids(),
        "modules": [
            "portfolio_object",
            "construction",
            "exposures",
            "risk_budget",
            "correlation",
            "quality",
            "attribution",
            "rebalancing",
            "scenarios",
            "monitoring",
            "graph",
        ],
        "api_prefix": "/v1/portfolio-intelligence/foundation",
    }


def dashboard() -> dict[str, Any]:
    rows = []
    for pid in list_portfolio_ids():
        p = get_portfolio(pid) or {}
        rows.append(
            {
                "portfolio_id": pid,
                "name": p.get("name"),
                "benchmark": p.get("benchmark"),
                "holding_count": len(p.get("holdings") or []),
                "cash_weight": p.get("cash_weight"),
                "objective": p.get("objective"),
            }
        )
    return {
        "ok": True,
        "version": PI_VERSION,
        "ask_wired": ASK_WIRED,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "portfolios": rows,
        "modules": health()["modules"],
        "fabricated": False,
    }


def portfolios() -> dict[str, Any]:
    return {"ok": True, "portfolios": dashboard()["portfolios"], "version": PI_VERSION}


def analyse(
    question: str,
    *,
    portfolio_id: Optional[str] = None,
    compare_with: Optional[str] = None,
) -> dict[str, Any]:
    return _analyse(question, portfolio_id=portfolio_id, compare_with=compare_with)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Diagnostics preview only — Ask production path uses KUL (no bypass)."""
    if not ASK_WIRED:
        return {
            "found": False,
            "ask_wired": False,
            "reason": "Portfolio Intelligence not wired into Ask until Acceptance = 100%",
            "recommendation_policy": RECOMMENDATION_POLICY,
            "fabricated": False,
        }
    out = analyse(question)
    return {
        "found": bool(out.get("ok") and out.get("summary")),
        "ask_wired": True,
        "ask_wired_via": ASK_WIRED_VIA,
        "enabled": True,
        "recommendation_policy": RECOMMENDATION_POLICY,
        **out,
    }


__all__ = [
    "analyse",
    "dashboard",
    "health",
    "portfolios",
    "soft_slice_for_ask_agi",
]
