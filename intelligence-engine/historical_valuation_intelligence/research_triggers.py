"""Emit research_timeline events when HVIE thresholds cross."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from historical_valuation_intelligence.models import ENGINE_CODE


def emit_research_events(
    symbol: str,
    *,
    metric: str,
    current_percentile: Optional[float],
    previous_regime: Optional[str],
    current_regime: Optional[str],
    current_value: Optional[float],
    median: Optional[float],
    actor: str = "hvie_runtime",
) -> list[dict[str, Any]]:
    """Write research_timeline rows for notable valuation transitions."""
    from institutional_warehouse import gateway

    ticker = str(symbol or "").strip().upper()
    today = date.today().isoformat()
    events: list[dict[str, Any]] = []

    if current_percentile is not None and current_percentile >= 90:
        events.append({
            "symbol": ticker,
            "date": today,
            "event": "valuation_highest_decile",
            "title": f"{metric.upper()} reached highest decile",
            "summary": (
                f"{ticker} {metric.upper()} is at the {current_percentile:.0f}th percentile "
                f"of its own history (current={current_value})."
            ),
            "severity": "valuation",
            "severity": "high",
        })
    if current_percentile is not None and current_percentile <= 10:
        events.append({
            "symbol": ticker,
            "date": today,
            "event": "valuation_lowest_decile",
            "title": f"{metric.upper()} at cheapest decile",
            "summary": (
                f"{ticker} {metric.upper()} is at the {current_percentile:.0f}th percentile "
                f"— Research Priority: deep valuation review."
            ),
            "severity": "valuation",
            "severity": "high",
        })

    if previous_regime and current_regime and previous_regime != current_regime:
        events.append({
            "symbol": ticker,
            "date": today,
            "event": "valuation_regime_changed",
            "title": f"Valuation regime {previous_regime} → {current_regime}",
            "summary": (
                f"{ticker} {metric.upper()} regime changed from {previous_regime} to "
                f"{current_regime} (current={current_value}, median={median})."
            ),
            "severity": "valuation",
            "severity": "medium",
        })

    if (
        current_value is not None
        and median is not None
        and median > 0
        and previous_regime
        and current_regime
    ):
        # Crossing historical median (premium ↔ discount)
        prev_side = "premium" if previous_regime in {"EXPENSIVE", "VERY_EXPENSIVE"} else "discount_or_fair"
        curr_above = current_value > median
        if prev_side == "premium" and not curr_above:
            events.append({
                "symbol": ticker,
                "date": today,
                "event": "valuation_crossed_median",
                "title": "Valuation crossed below historical median",
                "summary": f"{ticker} {metric.upper()} moved from premium to at/below median {median}.",
                "severity": "valuation",
                "severity": "medium",
            })

    written = []
    for ev in events:
        # research_timeline key is (symbol, date, event).
        row = {
            "symbol": ev["symbol"],
            "date": ev["date"],
            "event": f"{ev['event']}: {ev['title']}",
            "guidance": ev["summary"],
            "results": f"metric={metric}; value={current_value}; percentile={current_percentile}",
            "management": "hvie_runtime",
        }
        try:
            gateway.write(
                "research_timeline", [row], source=ENGINE_CODE, actor=actor,
                reason=f"hvie_trigger:{ev['event']}",
            )
            written.append(ev)
        except Exception:
            pass
    return written
