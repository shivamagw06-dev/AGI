"""Market health score 0–100 with component breakdown."""

from __future__ import annotations

from typing import Any

from market_intelligence_engine.constitution import CONFIDENCE_METHODOLOGY, widget_provenance


def _clamp(score: float) -> int:
    return max(0, min(100, int(round(score))))


def market_health_score(
    *,
    breadth: dict[str, Any],
    flows: dict[str, Any],
    overview: dict[str, Any],
    sectors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Composite market health — structural conditions, not expected return."""
    components: dict[str, dict[str, Any]] = {}

    adv = int(breadth.get("advancing") or 0)
    dec = int(breadth.get("declining") or 0)
    adv_ratio = adv / max(1, adv + dec)
    breadth_score = _clamp(40 + 60 * adv_ratio)
    components["breadth"] = {
        "score": breadth_score,
        "contribution_weight": 0.20,
        "detail": f"Advance/decline ratio {adv_ratio:.2f} ({adv}↑ vs {dec}↓)",
    }

    sample = int(breadth.get("sample_size") or 0)
    liquidity_score = _clamp(min(100, 35 + sample / 25))
    components["liquidity"] = {
        "score": liquidity_score,
        "contribution_weight": 0.10,
        "detail": f"{sample} securities with consecutive daily price observations",
    }

    avg_ret = breadth.get("average_return_pct")
    if avg_ret is not None:
        momentum_score = _clamp(50 + float(avg_ret) * 15)
    else:
        momentum_score = 50
    components["momentum"] = {
        "score": momentum_score,
        "contribution_weight": 0.15,
        "detail": f"Average 1-day return {avg_ret}%" if avg_ret is not None else "Momentum unavailable",
    }

    if flows.get("available") and flows.get("trend_5d") is not None:
        trend = float(flows["trend_5d"])
        flow_score = _clamp(50 + min(30, max(-30, trend / 100)))
    else:
        flow_score = 45
    components["institutional_flows"] = {
        "score": flow_score,
        "contribution_weight": 0.15,
        "detail": (
            f"5-day combined FII+DII trend {flows.get('trend_5d')}"
            if flows.get("trend_5d") is not None
            else "Institutional flow history limited or latest session unavailable"
        ),
    }

    pe_cov = float((overview.get("coverage") or {}).get("pct") or 0)
    valuation_score = _clamp(pe_cov * 1.1)
    components["valuation"] = {
        "score": valuation_score,
        "contribution_weight": 0.15,
        "detail": f"PE coverage {pe_cov:.1f}% of valuation universe",
    }

    med_abs = None
    if avg_ret is not None:
        med_abs = abs(float(breadth.get("median_return_pct") or avg_ret))
    vol_score = _clamp(85 - (med_abs or 0) * 8) if med_abs is not None else 55
    components["volatility"] = {
        "score": vol_score,
        "contribution_weight": 0.10,
        "detail": "Lower short-term dispersion supports higher structural health",
    }

    # Macro/credit placeholders until macro series wired into MIE pack
    components["macro"] = {
        "score": 55,
        "contribution_weight": 0.075,
        "detail": "Macro overlay pending full warehouse macro series integration",
        "status": "partial",
    }
    components["credit"] = {
        "score": 55,
        "contribution_weight": 0.075,
        "detail": "Credit conditions overlay pending warehouse credit series",
        "status": "partial",
    }

    overall = 0.0
    for comp in components.values():
        overall += comp["score"] * comp["contribution_weight"]

    pctiles = [s.get("historical_percentile") for s in sectors if s.get("historical_percentile") is not None]
    market_hist_pct = round(sum(pctiles) / len(pctiles), 1) if pctiles else None

    return {
        "overall": _clamp(overall),
        "components": components,
        "market_historical_percentile": market_hist_pct,
        "confidence_methodology": CONFIDENCE_METHODOLOGY,
        "provenance": widget_provenance(
            source="market_intelligence_engine.health",
            table="multiple",
            coverage=overview.get("coverage"),
            snapshot_date=overview.get("valuation_date"),
        ),
    }
