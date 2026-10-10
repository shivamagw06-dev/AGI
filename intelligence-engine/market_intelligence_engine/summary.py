"""AGI market summary — interpretation, not recommendation."""

from __future__ import annotations

from typing import Any


def market_summary(
    overview: dict[str, Any],
    sectors: list[dict[str, Any]],
    breadth: dict[str, Any],
    flows: dict[str, Any],
    *,
    regime: dict[str, Any] | None = None,
    health: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []

    if regime and regime.get("regime"):
        parts.append(
            f"Market regime: {regime['regime']}. {regime.get('explanation', '').rstrip('.')}."
        )

    if health and health.get("overall") is not None:
        parts.append(f"Overall market health score: {health['overall']}/100.")

    avg_pe = (overview.get("averages") or {}).get("pe")
    if avg_pe is not None:
        parts.append(f"The covered universe trades at a median P/E of {avg_pe:.1f}x.")

    below = [s for s in sectors if s.get("historical_range_status") == "Below Historical Range"]
    above = [s for s in sectors if s.get("historical_range_status") == "Above Historical Range"]
    if below:
        parts.append(
            f"{', '.join(s['sector'] for s in below[:3])} "
            f"{' sits' if len(below) == 1 else ' sit'} below historical valuation ranges."
        )
    if above:
        parts.append(
            f"{above[0]['sector']} continues above its historical valuation range."
        )

    if breadth.get("ok"):
        tracked = breadth.get("tracked_universe") or breadth.get("sample_size")
        cov_pct = breadth.get("coverage_pct")
        parts.append(
            f"Market breadth is {breadth.get('heatmap', 'mixed').lower()} "
            f"({breadth.get('advancing', 0)} advancing vs {breadth.get('declining', 0)} declining "
            f"among {tracked} tracked securities"
            + (f", {cov_pct}% of valuation universe" if cov_pct is not None else "")
            + ")."
        )

    if flows.get("available") and flows.get("explanation"):
        parts.append(flows["explanation"])

    if not parts:
        return (
            "Market summary will populate once warehouse valuation and flow coverage are complete. "
            "No investment advice is implied."
        )
    parts.append("This is institutional market intelligence for research prioritisation, not investment advice.")
    return " ".join(parts)
