"""Opportunity detection — research candidates, not buy/sell calls."""

from __future__ import annotations

from typing import Any, Callable


def _card(
    kind: str,
    title: str,
    row: dict[str, Any],
    *,
    why: str,
    priority: int = 50,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "title": title,
        "symbol": row.get("symbol"),
        "company_name": row.get("company_name"),
        "sector": row.get("sector"),
        "industry": row.get("industry"),
        "why": why,
        "evidence": {
            "pe": row.get("pe"),
            "pb": row.get("pb"),
            "percentile": row.get("percentile"),
            "consensus_upside": row.get("consensus_upside"),
            "analyst_count": row.get("analyst_count"),
            "primary_metric": row.get("primary_metric"),
            "primary_value": row.get("primary_value"),
            "provider_coverage": row.get("provider_coverage"),
        },
        "historical_context": f"Historical percentile {row.get('percentile')}" if row.get("percentile") is not None else "Historical coverage limited",
        "peer_context": f"Sector {row.get('sector')}" if row.get("sector") else None,
        "coverage": row.get("source") or "warehouse",
        "research_priority": priority,
    }


def detect_opportunities(universe: dict[str, Any], *, limit_per_kind: int = 8) -> dict[str, Any]:
    rows = universe.get("rows") or []
    if not rows:
        return {"ok": False, "error": "empty_universe", "cards": []}

    by_industry: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ind = row.get("industry")
        if ind:
            by_industry.setdefault(str(ind), []).append(row)

    cards: list[dict[str, Any]] = []

    # Relative value — below industry median P/E
    rel: list[dict[str, Any]] = []
    for row in rows:
        ind = row.get("industry")
        peers = by_industry.get(str(ind) or "", [])
        med = _median([p.get("pe") for p in peers if p.get("pe") is not None])
        if row.get("pe") is not None and med is not None and row["pe"] < med * 0.85:
            rel.append((med - row["pe"], row))
    rel.sort(key=lambda t: -t[0])
    for _, row in rel[:limit_per_kind]:
        cards.append(_card("relative_value", "Relative Value", row,
                           why=f"P/E {row['pe']:.1f}x trades below industry median.", priority=75))

    # Historical discount — bottom decile percentile
    for row in sorted([r for r in rows if r.get("percentile") is not None], key=lambda r: r["percentile"])[:limit_per_kind]:
        if row["percentile"] <= 15:
            cards.append(_card("historical_discount", "Historical Discount", row,
                               why=f"Valuation percentile {row['percentile']:.0f}% — bottom historical range.", priority=80))

    # Historical premium
    for row in sorted([r for r in rows if r.get("percentile") is not None], key=lambda r: -r["percentile"])[:limit_per_kind]:
        if row["percentile"] >= 85:
            cards.append(_card("historical_premium", "Historical Premium", row,
                               why=f"Valuation percentile {row['percentile']:.0f}% — top historical range.", priority=55))

    # Valuation compression / expansion
    for row in sorted([r for r in rows if r.get("pe_change_pct") is not None], key=lambda r: r["pe_change_pct"])[:limit_per_kind]:
        if row["pe_change_pct"] <= -3:
            cards.append(_card("valuation_compression", "Valuation Compression", row,
                               why=f"P/E compressed {row['pe_change_pct']:+.1f}% vs prior observation.", priority=70))
    for row in sorted([r for r in rows if r.get("pe_change_pct") is not None], key=lambda r: -r["pe_change_pct"])[:limit_per_kind]:
        if row["pe_change_pct"] >= 3:
            cards.append(_card("valuation_expansion", "Valuation Expansion", row,
                               why=f"P/E expanded {row['pe_change_pct']:+.1f}% vs prior observation.", priority=60))

    # Consensus upside with reasonable coverage
    for row in sorted([r for r in rows if r.get("consensus_upside") is not None], key=lambda r: -(r["consensus_upside"] or 0))[:limit_per_kind]:
        if (row.get("consensus_upside") or 0) >= 10 and (row.get("analyst_count") or 0) >= 3:
            cards.append(_card("earnings_rerating", "Consensus Gap", row,
                               why=f"Consensus upside {row['consensus_upside']:.1f}% with analyst coverage.", priority=72))

    # De-dupe by symbol+kind, rank by priority
    seen: set[tuple[str, str]] = set()
    unique = []
    for c in sorted(cards, key=lambda x: -x["research_priority"]):
        key = (c["symbol"], c["kind"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)

    return {"ok": True, "count": len(unique), "cards": unique[: limit_per_kind * 4]}


def research_priorities(universe: dict[str, Any], opportunities: dict[str, Any], *, limit: int = 15) -> list[dict[str, Any]]:
    cards = opportunities.get("cards") or []
    ranked = sorted(cards, key=lambda c: -c.get("research_priority", 0))[:limit]
    out = []
    for i, card in enumerate(ranked, start=1):
        confidence = _research_confidence(card)
        ev = card.get("evidence") or {}
        selection_reasons = _selection_reasons(card, ev)
        out.append({
            "rank": i,
            "symbol": card.get("symbol"),
            "company_name": card.get("company_name"),
            "reason": card.get("why"),
            "selection_reasons": selection_reasons,
            "confidence": confidence,
            "confidence_note": "Evidence reliability — not expected return",
            "kind": card.get("kind"),
        })
    return out


def _selection_reasons(card: dict[str, Any], ev: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if ev.get("percentile") is not None:
        reasons.append(f"Historical valuation percentile {ev['percentile']:.0f}%")
    if ev.get("pe") is not None:
        reasons.append("PE ratio available for peer comparison")
    if ev.get("provider_coverage"):
        reasons.append("Provider ratio coverage present")
    if (ev.get("analyst_count") or 0) >= 3:
        reasons.append(f"Analyst coverage ({ev['analyst_count']} estimates)")
    if card.get("why"):
        reasons.append(card["why"])
    return reasons[:5]


def _research_confidence(card: dict[str, Any]) -> int:
    """Derive confidence from data quality — not a fixed formula."""
    ev = card.get("evidence") or {}
    score = 35
    if ev.get("percentile") is not None:
        score += 18
    if ev.get("pe") is not None or ev.get("pb") is not None:
        score += 12
    if ev.get("provider_coverage"):
        score += 8
    if (ev.get("analyst_count") or 0) >= 3:
        score += 10
    if ev.get("consensus_upside") is not None:
        score += 7
    if card.get("coverage") in {"warehouse", "upstox"}:
        score += 5
    # Modest priority lift — should not collapse everyone to ~95%.
    score += min(12, (card.get("research_priority") or 0) // 8)
    return min(99, max(35, score))


def _median(values: list[Any]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    clean.sort()
    mid = len(clean) // 2
    return clean[mid] if len(clean) % 2 else (clean[mid - 1] + clean[mid]) / 2
