"""P2.6 Live Market Context — production façade (standard engine contract)."""

from __future__ import annotations

from typing import Any

from live_market_context.context import build_market_context
from live_market_context.schema import (
    ENGINE_CODE,
    ENGINE_NAME,
    MILESTONE,
    PROGRAMME,
    RUNTIME_BUDGET_S,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from phase2_investment_intelligence.contract import build_engine_contract
except Exception:  # pragma: no cover
    build_engine_contract = None  # type: ignore


def health() -> dict[str, Any]:
    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {}
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "contract": contract,
        "runtime_budget_s": RUNTIME_BUDGET_S,
        "fail_closed_on_missing_quote": True,
        "extends_intelligence": True,
        "replaces_baseline": False,
        "implementation_pr_checklist": [
            "What intelligence did we add?",
            "What measurable metric improved?",
            "What metric stayed unchanged?",
            "Did IAT still pass?",
            "Did UNKNOWN drift remain zero?",
        ],
    }


def analyse(
    ticker: str,
    *,
    force: bool = False,
    intrinsic_value: float | None = None,
) -> dict[str, Any]:
    """Market context pack for one ticker."""
    ctx = build_market_context(ticker, force=force, intrinsic_value=intrinsic_value)
    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {"engine": ENGINE_CODE}
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "contract": contract,
        "ticker": ctx["ticker"],
        "ok": ctx["ok"],
        "score": ctx.get("score"),
        "evidence": ctx.get("evidence") or [],
        "confidence": ctx.get("confidence"),
        "freshness": ctx.get("freshness") or {},
        "lineage": ctx.get("lineage") or [],
        "panel": {
            "ltp": ctx.get("ltp"),
            "currency": ctx.get("currency"),
            "change_pct": ctx.get("change_pct"),
            "provider": ctx.get("provider"),
            "price_freshness": ctx.get("price_freshness"),
            "liquidity": ctx.get("liquidity"),
            "relative_strength": ctx.get("relative_strength"),
            "distance_to_intrinsic": ctx.get("distance_to_intrinsic"),
            "market_status": ctx.get("market_status"),
        },
        "degraded": not ctx.get("ok"),
        "degraded_reason": ctx.get("error") if not ctx.get("ok") else None,
        "failure_mode": {
            "strategy": "degrade_gracefully",
            "block_unrelated_engines": False,
            "fabricated": False,
        },
        "fabricated": False,
        "baseline_compatible": True,
        "failover_from": ctx.get("failover_from"),
        "fail_closed": ctx.get("fail_closed"),
    }


def package_for_ask_agi(
    query: str,
    *,
    ticker: str | None = None,
    intrinsic_value: float | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Soft slice for Ask AGI / Decision Engine — never raises."""
    if not ticker:
        return {
            "enabled": True,
            "engine": ENGINE_CODE,
            "soft": True,
            "skipped": True,
            "reason": "ticker_required",
            "fabricated": False,
            "baseline_compatible": True,
            "failure_mode": {"strategy": "degrade_gracefully", "block_unrelated_engines": False},
        }
    try:
        pack = analyse(str(ticker), force=force, intrinsic_value=intrinsic_value)
        pack["soft"] = True
        pack["query"] = query
        return pack
    except Exception as exc:
        return {
            "enabled": True,
            "engine": ENGINE_CODE,
            "soft": True,
            "ticker": str(ticker).upper(),
            "degraded": True,
            "degraded_reason": str(exc)[:200],
            "score": None,
            "evidence": [],
            "confidence": 0.0,
            "freshness": {"stale": True},
            "lineage": [],
            "fabricated": False,
            "baseline_compatible": True,
            "failure_mode": {
                "strategy": "degrade_gracefully",
                "block_unrelated_engines": False,
                "fabricated": False,
            },
        }
