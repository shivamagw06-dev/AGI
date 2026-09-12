"""P6.5 Theme Intelligence — evolving themes via graph membership + opportunity strength."""

from __future__ import annotations

from typing import Any

from autonomous_research.schema import THEME_CATALOG
from autonomous_research.util import as_float, oie_of


# Map graph theme / sector keys into catalog themes
_SECTOR_THEME = {
    "banks": "Banking",
    "it_services": "AI",
    "power": "Power",
    "defence": "Defence",
    "cement": "Infrastructure",
    "auto": "Manufacturing",
    "pharma": "Pharma",
}


def build_theme_intelligence(company_packs: list[dict[str, Any]]) -> dict[str, Any]:
    themes: dict[str, dict[str, Any]] = {
        t: {"theme": t, "members": [], "scores": [], "n": 0, "strength": 0.0} for t in THEME_CATALOG
    }

    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = oie_of(p)
        score = as_float(oie.get("score")) or 50.0
        graph = p.get("knowledge_graph") or {}
        member_themes = list(graph.get("themes") or [])
        sector = graph.get("sector_key") or ((p.get("memory") or {}).get("sector_history") or {}).get("sector_key")
        if sector in _SECTOR_THEME:
            member_themes.append(_SECTOR_THEME[sector])
        # Soft catalog matches
        for th in list(member_themes):
            for cat in THEME_CATALOG:
                if cat.lower() == str(th).lower() or str(th).lower() in cat.lower():
                    member_themes.append(cat)
        for th in sorted(set(member_themes)):
            if th not in themes:
                themes[th] = {"theme": th, "members": [], "scores": [], "n": 0, "strength": 0.0}
            themes[th]["members"].append(p.get("display") or p.get("entity"))
            themes[th]["scores"].append(score)

    out = []
    for th, row in themes.items():
        if not row["scores"] and th not in THEME_CATALOG:
            continue
        n = len(row["scores"])
        avg = sum(row["scores"]) / n if n else 0.0
        # Strength: membership density + avg opportunity (graph propagation proxy)
        strength = round(min(100.0, avg * 0.7 + min(30.0, n * 8)), 1) if n else 0.0
        out.append(
            {
                "theme": th,
                "n": n,
                "members": sorted(set(row["members"])),
                "avg_opportunity_score": round(avg, 1) if n else None,
                "strength": strength,
                "propagation": "investment_knowledge_graph.themes+sector_map+opportunity_scores",
            }
        )
    out.sort(key=lambda r: (-r["strength"], r["theme"]))
    return {
        "themes": out,
        "active_n": sum(1 for r in out if r["n"] > 0),
        "catalog": list(THEME_CATALOG),
    }
