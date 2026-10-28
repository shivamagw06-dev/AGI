"""Top market drivers — magnitude, direction, affected sectors."""

from __future__ import annotations

from typing import Any

from market_intelligence_engine.constitution import widget_provenance


def market_drivers(
    *,
    sectors: list[dict[str, Any]],
    rotation: dict[str, Any],
    flows: dict[str, Any],
    breadth: dict[str, Any],
    limit: int = 5,
) -> dict[str, Any]:
    """Rank institutional drivers of today's market state."""
    candidates: list[dict[str, Any]] = []

    # Valuation-led sector moves
    for s in sectors:
        prem = s.get("benchmark_premium_pct") if s.get("benchmark_premium_pct") is not None else s.get("premium_pct")
        pct = s.get("historical_percentile")
        if prem is not None and abs(float(prem)) >= 8:
            candidates.append({
                "driver": "Sector Valuation",
                "direction": "expansion" if float(prem) > 0 else "compression",
                "magnitude": abs(float(prem)),
                "affected_sectors": [s["sector"]],
                "persistence": "structural" if (pct or 0) >= 70 or (pct or 100) <= 30 else "monitor",
                "detail": (
                    f"{s['sector']} trades {prem:+.1f}% vs Upstox sector benchmark "
                    f"(historical percentile {pct}%)"
                    if pct is not None
                    else f"{s['sector']} valuation premium/discount {prem:+.1f}%"
                ),
            })

    # Rotation
    for bucket, label in (("entering", "Rotation Inflow"), ("leaving", "Rotation Outflow")):
        for row in (rotation.get(bucket) or [])[:2]:
            chg = row.get("median_pe_change_pct") or row.get("avg_pe_change_pct")
            if chg is None:
                continue
            candidates.append({
                "driver": label,
                "direction": "inflow" if bucket == "entering" else "outflow",
                "magnitude": abs(float(chg)),
                "affected_sectors": [row["sector"]],
                "persistence": "temporary" if abs(float(chg)) < 25 else "structural",
                "detail": f"{row['sector']} median P/E change {float(chg):+.1f}%",
            })

    # Institutional flows
    if flows.get("available"):
        t5 = flows.get("trend_5d")
        if t5 is not None and abs(float(t5)) > 0:
            candidates.append({
                "driver": "Institutional Flows",
                "direction": "supportive" if float(t5) > 0 else "headwind",
                "magnitude": min(100, abs(float(t5)) / 50),
                "affected_sectors": ["Market-wide"],
                "persistence": "monitor",
                "detail": f"Combined FII+DII 5-day trend {float(t5):+,.0f} crore",
            })

    # Breadth participation
    if breadth.get("ok"):
        heatmap = breadth.get("heatmap") or "Neutral"
        if heatmap not in ("Neutral",):
            candidates.append({
                "driver": "Market Breadth",
                "direction": "positive" if "Bull" in heatmap else "negative",
                "magnitude": 50 if "Strong" in heatmap else 30,
                "affected_sectors": ["Market-wide"],
                "persistence": "temporary",
                "detail": (
                    f"Breadth {heatmap}: {breadth.get('advancing')} advancing vs "
                    f"{breadth.get('declining')} declining"
                ),
            })

    # De-dupe by driver name, keep highest magnitude
    seen: dict[str, dict[str, Any]] = {}
    for c in sorted(candidates, key=lambda x: -x["magnitude"]):
        key = c["driver"]
        if key not in seen or c["magnitude"] > seen[key]["magnitude"]:
            seen[key] = c

    ranked = sorted(seen.values(), key=lambda x: -x["magnitude"])[:limit]

    return {
        "drivers": ranked,
        "count": len(ranked),
        "provenance": widget_provenance(
            source="market_intelligence_engine.drivers",
            table="derived",
            coverage={"sectors": len(sectors)},
            snapshot_date=breadth.get("date"),
        ),
    }
