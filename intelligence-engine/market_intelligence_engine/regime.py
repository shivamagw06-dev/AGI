"""Market regime classification — institutional cycle labels, not mood tags."""

from __future__ import annotations

from typing import Any

from market_intelligence_engine.constitution import widget_provenance

REGIME_LABELS = (
    "Expansion",
    "Early Expansion",
    "Mid Cycle",
    "Late Cycle",
    "Correction",
    "Recovery",
    "Bear Market",
    "Capitulation",
    "Transition",
)


def classify_market_regime(
    *,
    breadth: dict[str, Any],
    flows: dict[str, Any],
    sectors: list[dict[str, Any]],
    overview: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic regime from breadth, flows, and sector valuation dispersion."""
    adv = int(breadth.get("advancing") or 0)
    dec = int(breadth.get("declining") or 0)
    total = adv + dec + int(breadth.get("unchanged") or 0)
    adv_ratio = adv / max(1, adv + dec)
    heatmap = str(breadth.get("heatmap") or "Neutral")
    avg_ret = breadth.get("average_return_pct")
    confirmation = breadth.get("confirmation") or {}
    bullish_confirmed = bool(confirmation.get("bullish_confirmed"))
    bearish_confirmed = bool(confirmation.get("bearish_confirmed"))

    flow_trend = flows.get("trend_5d") if flows.get("available") else None
    flow_positive = flow_trend is not None and float(flow_trend) > 0

    premium_sectors = sum(1 for s in sectors if (s.get("historical_percentile") or 0) >= 75)
    cheap_sectors = sum(1 for s in sectors if (s.get("historical_percentile") or 100) <= 25)
    sector_count = len([s for s in sectors if s.get("historical_percentile") is not None])

    regime = "Transition"
    drivers: list[str] = []

    if heatmap in ("Strong Bearish", "Bearish") and bearish_confirmed and adv_ratio < 0.35:
        if dec > adv * 3 and total >= 50:
            regime = "Capitulation"
            drivers.append("Breadth heavily negative with broad participation to the downside")
        else:
            regime = "Bear Market"
            drivers.append("Declining breadth with risk-off participation")
    elif heatmap in ("Strong Bearish", "Bearish") and bearish_confirmed:
        regime = "Correction"
        drivers.append("Pullback in market breadth despite mixed participation")
    elif heatmap in ("Strong Bullish", "Bullish") and bullish_confirmed and adv_ratio >= 0.65:
        if premium_sectors >= max(2, sector_count // 3):
            regime = "Late Cycle"
            drivers.append("Broad participation but several sectors above historical valuation bands")
        elif cheap_sectors >= max(2, sector_count // 4):
            regime = "Early Expansion"
            drivers.append("Improving breadth with valuation still below historical ranges in key sectors")
        else:
            regime = "Expansion"
            drivers.append("Breadth improving with balanced sector valuation")
    elif heatmap in ("Strong Bullish", "Bullish") and bullish_confirmed:
        regime = "Recovery"
        drivers.append("Breadth recovering from prior weakness")
    elif 0.45 <= adv_ratio <= 0.55:
        regime = "Mid Cycle"
        drivers.append("Balanced advance/decline participation")
    else:
        regime = "Transition"
        if heatmap in ("Strong Bullish", "Bullish", "Strong Bearish", "Bearish"):
            drivers.append("Latest breadth move awaits multi-session confirmation")
        else:
            drivers.append("Mixed signals across breadth and sector valuation")

    if flow_positive:
        drivers.append("Institutional flows supportive on recent sessions")
    elif flow_trend is not None and float(flow_trend) < 0:
        drivers.append("Institutional flows negative on recent sessions")

    if avg_ret is not None:
        if float(avg_ret) >= 0.5:
            drivers.append("Short-term momentum positive")
        elif float(avg_ret) <= -0.5:
            drivers.append("Short-term momentum negative")

    pe_cov = (overview.get("coverage") or {}).get("pct")
    if pe_cov is not None and float(pe_cov) < 50:
        drivers.append(f"Valuation coverage limited ({pe_cov}% of universe)")

    return {
        "regime": regime,
        "participation": {
            "advance_decline_ratio": round(adv_ratio, 3),
            "advancing": adv,
            "declining": dec,
            "tracked": total,
        },
        "confirmation": confirmation,
        "drivers": drivers[:6],
        "explanation": (
            f"Market regime classified as {regime} because "
            + "; ".join(drivers[:3])
            + "."
        ),
        "provenance": widget_provenance(
            source="warehouse.daily_market_history + historical_valuation",
            table="daily_market_history",
            coverage=breadth.get("coverage"),
            snapshot_date=breadth.get("date"),
        ),
    }
