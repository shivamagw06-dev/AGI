"""P5.3 Portfolio Operations — monitor holdings via compiled intelligence (no allocation)."""

from __future__ import annotations

from typing import Any

from investment_operations.util import as_float, priority_rank, resolve_ticker


def build_portfolio_operations(
    company_packs: list[dict[str, Any]],
    *,
    holdings: list[str] | None = None,
    portfolio_id: str = "default",
) -> dict[str, Any]:
    if not holdings:
        return {
            "portfolio_id": portfolio_id,
            "holdings": [],
            "affected_holdings": [],
            "expected_impact": {
                "note": "No holdings provided — pass holdings= to evaluate portfolio impact.",
                "direction": "n/a",
                "qualitative": "neutral",
            },
            "research_required": [],
            "urgency": "none",
            "concentration": {},
            "recommendation_policy": "no_allocation_advice",
        }

    by_entity = {p.get("entity"): p for p in company_packs}
    by_display = {(p.get("display") or "").upper(): p for p in company_packs}
    affected = []
    research = []
    sector_counts: dict[str, int] = {}
    theme_counts: dict[str, int] = {}
    impact_votes: list[float] = []

    for h in holdings:
        key = resolve_ticker(h)
        p = by_entity.get(key) or by_display.get(h.upper())
        if not p:
            affected.append(
                {
                    "holding": h.upper(),
                    "status": "not_in_coverage",
                    "research_required": True,
                    "urgency": "Medium",
                }
            )
            research.append({"holding": h.upper(), "reason": "Not in current compiled coverage"})
            continue
        oie = p.get("opportunity") or {}
        score = as_float(oie.get("score")) or 50.0
        priority = oie.get("research_priority") or "Monitor"
        kd = {}
        if isinstance(oie.get("opportunity"), dict):
            kd = oie["opportunity"].get("knowledge_delta") or {}
        blockers = oie.get("blockers") or []
        high_b = [b for b in blockers if b.get("severity") == "High"]
        improving = score >= 60 and priority_rank(priority) <= 2 and not high_b
        deteriorating = score < 40 or bool(high_b) or (kd.get("status") == "UPDATED" and score < 50)

        # Qualitative impact vote from opportunity + blockers (not a return forecast)
        vote = 0.0
        if improving:
            vote += 0.6
        if deteriorating:
            vote -= 0.7
        if kd.get("status") and kd.get("status") != "UNCHANGED":
            vote += 0.1 if score >= 55 else -0.2
        impact_votes.append(vote)

        sk = ((p.get("memory") or {}).get("sector_history") or {}).get("sector_key") or (
            (p.get("knowledge_graph") or {}).get("sector_key")
        ) or "unknown"
        sector_counts[sk] = sector_counts.get(sk, 0) + 1
        for th in (p.get("knowledge_graph") or {}).get("themes") or []:
            theme_counts[th] = theme_counts.get(th, 0) + 1

        row = {
            "holding": p.get("display") or h.upper(),
            "entity": p.get("entity"),
            "status": "improving" if improving else ("deteriorating" if deteriorating else "stable"),
            "opportunity_score": score,
            "research_priority": priority,
            "delta_status": kd.get("status"),
            "blockers": [b.get("title") for b in high_b[:3]],
            "why_now": oie.get("why_now"),
            "research_required": priority_rank(priority) <= 2 or bool(high_b) or deteriorating,
            "urgency": priority if priority_rank(priority) <= 2 else ("High" if deteriorating else "Low"),
        }
        affected.append(row)
        if row["research_required"]:
            research.append(
                {
                    "holding": row["holding"],
                    "reason": row["why_now"] or f"Status {row['status']}; priority {priority}",
                    "urgency": row["urgency"],
                }
            )

    avg_vote = sum(impact_votes) / len(impact_votes) if impact_votes else 0.0
    if avg_vote >= 0.25:
        qualitative = "positive"
    elif avg_vote <= -0.25:
        qualitative = "negative"
    else:
        qualitative = "neutral"

    urgency = "High" if any(r.get("urgency") in {"Critical", "High"} for r in research) else (
        "Medium" if research else "Low"
    )

    return {
        "portfolio_id": portfolio_id,
        "holdings": [h.upper() for h in holdings],
        "affected_holdings": affected,
        "expected_impact": {
            "qualitative": qualitative,
            "vote_average": round(avg_vote, 3),
            "note": "Qualitative portfolio impact from compiled opportunity/delta/blockers — not a return forecast or allocation advice.",
        },
        "research_required": research,
        "urgency": urgency,
        "concentration": {
            "sectors": dict(sorted(sector_counts.items())),
            "themes": dict(sorted(theme_counts.items())),
        },
        "recommendation_policy": "no_allocation_advice",
        "issues_recommendations": False,
    }
