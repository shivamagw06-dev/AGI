"""Corporate / Strategy Intelligence — structured evolution from event timeline."""

from __future__ import annotations

from typing import Any


# Lightweight keyword → strategy theme map (observations, not LLM rediscovery)
_THEME_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("cloud", "saas", "digital"), "cloud / digital expansion"),
    (("artificial intelligence", " ai ", "genai", "machine learning"), "AI investments"),
    (("acquisition", "acquired", "merger", "buyout"), "acquisitions / M&A"),
    (("buyback", "share repurchase"), "capital return — buyback"),
    (("dividend",), "capital return — dividend"),
    (("capex", "capacity", "plant", "greenfield", "brownfield"), "capacity / capex"),
    (("fda", "warning letter", "inspection", "anda"), "regulatory / quality"),
    (("ceo", "md appointed", "management change", "resign"), "leadership change"),
    (("guidance", "outlook raised", "outlook lowered"), "guidance revision"),
    (("international", "export", "overseas", "global"), "international expansion"),
    (("ev ", "electric vehicle", "battery"), "EV transition"),
    (("covid", "pandemic"), "covid shock"),
)


def derive_corporate_history(entity: str, *, event_timeline: dict[str, Any] | None = None) -> dict[str, Any]:
    by_year = (event_timeline or {}).get("by_year") if isinstance(event_timeline, dict) else {}
    strategy: dict[str, Any] = {}
    for year, rows in sorted((by_year or {}).items()):
        themes: list[str] = []
        titles = " ".join(str(r.get("title") or "") for r in rows).lower()
        evidence = " ".join(str(r.get("evidence") or "") for r in rows).lower()
        blob = f" {titles} {evidence} "
        for keys, theme in _THEME_RULES:
            if any(k in blob for k in keys):
                themes.append(theme)
        # Always keep filing milestones
        if any(r.get("type") == "financial_result" for r in rows):
            themes.append("reported results")
        # Dedup preserve order
        seen: set[str] = set()
        uniq = []
        for t in themes:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        if uniq or rows:
            strategy[f"FY{year[-2:]}" if len(year) == 4 else year] = {
                "year": year,
                "strategy_themes": uniq,
                "event_count": len(rows),
                "sample_events": [r.get("title") for r in rows[:4]],
            }

    return {
        "available": bool(strategy),
        "entity": entity,
        "strategy_evolution": strategy,
        "observations": [
            f"{k}: {', '.join(v.get('strategy_themes') or ['events recorded'])}"
            for k, v in list(strategy.items())[-6:]
        ],
        "lineage": [{"source": "event_timeline_theme_extract", "years": len(strategy)}],
        "note": "Themes are rule-derived from structured events — not free-form LLM invention.",
    }
