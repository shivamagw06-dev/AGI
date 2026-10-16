"""P6.1 Research Planner — decide what research should be performed."""

from __future__ import annotations

from typing import Any

from autonomous_research.schema import RESEARCH_TYPES
from autonomous_research.util import as_float, delta_of, oie_of, priority_rank, today


def build_research_plan(
    company_packs: list[dict[str, Any]],
    *,
    holdings: list[str] | None = None,
    catalysts: dict[str, Any] | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    holdings_set = {h.upper() for h in (holdings or [])}
    plans = []

    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = oie_of(p)
        kd = delta_of(p)
        score = as_float(oie.get("score")) or 0.0
        priority = oie.get("research_priority") or "Monitor"
        in_port = (p.get("display") or "").upper() in holdings_set or (p.get("entity") or "") in holdings_set
        cats = oie.get("catalysts") or []
        high_cat = [c for c in cats if c.get("importance") == "High"]
        blockers = oie.get("blockers") or []
        high_block = [b for b in blockers if b.get("severity") == "High"]

        research_type = _infer_type(kd, high_cat, high_block, oie)
        deadline = "same_day" if priority == "Critical" or (in_port and priority_rank(priority) <= 1) else (
            "this_week" if priority_rank(priority) <= 2 or (kd.get("status") not in {None, "UNCHANGED"}) else "monitor"
        )
        urgency = (
            score * 0.4
            + (4 - min(priority_rank(priority), 4)) * 14
            + min(18.0, (as_float(kd.get("n_field_changes")) or 0) * 3)
            + len(high_cat) * 8
            + len(high_block) * 5
            + (12 if in_port else 0)
        )

        plans.append(
            {
                "research_plan": {
                    "company": p.get("display") or p.get("entity"),
                    "entity": p.get("entity"),
                    "research_type": research_type,
                    "priority": priority,
                    "deadline": deadline,
                    "evidence": {
                        "opportunity_score": score,
                        "why_now": oie.get("why_now"),
                        "knowledge_delta": {
                            "status": kd.get("status"),
                            "n_field_changes": kd.get("n_field_changes"),
                            "summary": kd.get("summary"),
                        },
                        "catalysts": [{"name": c.get("name"), "importance": c.get("importance")} for c in cats[:4]],
                        "blockers": [{"title": b.get("title"), "severity": b.get("severity")} for b in blockers[:4]],
                        "portfolio_relevant": in_port,
                        "memory_version": (p.get("memory") or {}).get("memory_version")
                        or (oie.get("freshness") or {}).get("memory_version"),
                    },
                },
                "urgency_score": round(urgency, 1),
            }
        )

    plans.sort(
        key=lambda x: (
            -x["urgency_score"],
            priority_rank(x["research_plan"].get("priority")),
            x["research_plan"].get("entity") or "",
        )
    )
    trimmed = plans[: max(1, min(int(limit), 100))]
    return {
        "session_date": today(),
        "n": len(trimmed),
        "research_types": list(RESEARCH_TYPES),
        "plans": [x["research_plan"] for x in trimmed],
        "urgency": [
            {"company": x["research_plan"]["company"], "urgency_score": x["urgency_score"]} for x in trimmed
        ],
    }


def _infer_type(
    kd: dict[str, Any],
    high_cat: list[dict[str, Any]],
    high_block: list[dict[str, Any]],
    oie: dict[str, Any],
) -> str:
    titles = " ".join(str(c.get("name") or "").lower() for c in high_cat)
    if "result" in titles or "earnings" in titles:
        if "preview" in titles:
            return "earnings_preview"
        return "earnings_review"
    if high_block:
        return "risk_update"
    if kd.get("status") and kd.get("status") != "UNCHANGED":
        return "company_update"
    if any(c.get("importance") == "High" for c in (oie.get("catalysts") or [])):
        return "event_analysis"
    return "company_update"
