"""Sector rotation and market explainability."""

from __future__ import annotations

from statistics import median
from typing import Any

# Cap extreme P/E % changes driven by tiny denominators or sign flips.
PE_CHANGE_CAP = 150.0


def _cap_pct(value: float, cap: float = PE_CHANGE_CAP) -> float:
    return max(-cap, min(cap, value))


def _median_pe_change(moves: list[float]) -> float:
    if not moves:
        return 0.0
    capped = [_cap_pct(float(m)) for m in moves]
    return round(float(median(capped)), 2)


def market_rotation(sectors: list[dict[str, Any]], universe: dict[str, Any]) -> dict[str, Any]:
    if not sectors:
        return {"ok": False, "error": "no_sectors"}

    # Rank sectors by median (winsorized) P/E change in member stocks.
    sector_moves: dict[str, list[float]] = {}
    for row in universe.get("rows") or []:
        sector = row.get("sector")
        chg = row.get("pe_change_pct")
        if sector and chg is not None:
            sector_moves.setdefault(str(sector), []).append(float(chg))

    ranked = []
    for sector, moves in sector_moves.items():
        med = _median_pe_change(moves)
        ranked.append({
            "sector": sector,
            "avg_pe_change_pct": med,  # legacy field name — value is median
            "median_pe_change_pct": med,
            "companies": len(moves),
        })
    ranked.sort(key=lambda r: r["median_pe_change_pct"])

    leaving = ranked[:3]
    entering = list(reversed(ranked[-3:]))

    explanation_parts = []
    if entering:
        top = entering[0]
        explanation_parts.append(
            f"Valuation expansion is concentrated in {top['sector']} "
            f"(median P/E change {top['median_pe_change_pct']:+.1f}%, capped at ±{PE_CHANGE_CAP:.0f}%), "
            "indicating multiple-led moves rather than a uniform market re-rating."
        )
    premium = sorted(
        [s for s in sectors if s.get("historical_percentile") is not None],
        key=lambda s: -(s.get("historical_percentile") or 0),
    )
    if premium:
        explanation_parts.append(
            f"{premium[0]['sector']} remains in the upper historical valuation band "
            f"(percentile ~{premium[0]['historical_percentile']:.0f}%)."
        )
    explanation_parts.append("Rotation context only — not a recommendation.")

    return {
        "ok": True,
        "leaving": leaving,
        "entering": entering,
        "rows": ranked,
        "pe_change_cap_pct": PE_CHANGE_CAP,
        "explanation": " ".join(explanation_parts),
    }


def market_explainability(universe: dict[str, Any], *, limit: int = 6) -> list[dict[str, Any]]:
    """Explain major sector-level multiple moves using attribution pattern."""
    from valuation_engine import attribution

    rows = universe.get("rows") or []
    sector_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("sector"):
            sector_groups.setdefault(str(row["sector"]), []).append(row)

    narratives = []
    for sector, members in sector_groups.items():
        if len(members) < 8:
            continue
        pe_changes = [m.get("pe_change_pct") for m in members if m.get("pe_change_pct") is not None]
        if not pe_changes:
            continue
        med_pe_chg = _median_pe_change([float(c) for c in pe_changes])
        if abs(med_pe_chg) < 1.5:
            continue
        # Representative member with largest move
        rep = max(members, key=lambda m: abs(m.get("pe_change_pct") or 0))
        before = {"pe": rep.get("prev_pe"), "pb": rep.get("prev_pb"), "cmp": rep.get("cmp"), "eps": rep.get("eps")}
        after = {"pe": rep.get("pe"), "pb": rep.get("pb"), "cmp": rep.get("cmp"), "eps": rep.get("eps")}
        entry = attribution.explain_change("pe", before, after)
        summary = entry.get("summary") or f"{sector} P/E moved {med_pe_chg:+.1f}% on median."
        if entry.get("uncomparable"):
            summary = (
                f"Valuation increased in {sector} (median P/E change {med_pe_chg:+.1f}%) "
                "because historical earnings data was unavailable — "
                "price/earnings attribution could not be decomposed."
            )
        narratives.append({
            "sector": sector,
            "symbol": rep.get("symbol"),
            "metric": "pe",
            "change_pct": med_pe_chg,
            "summary": summary,
            "drivers": entry.get("drivers") or [],
        })
        if len(narratives) >= limit:
            break
    return narratives
