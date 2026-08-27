"""P6.7 Portfolio Review Automation — periodic reviews, no allocation advice."""

from __future__ import annotations

from typing import Any

from autonomous_research.util import delta_of, now_iso, oie_of, priority_rank


def build_portfolio_review(
    company_packs: list[dict[str, Any]],
    *,
    holdings: list[str] | None = None,
    portfolio_ops: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not holdings:
        return {
            "ok": True,
            "holdings": [],
            "note": "No holdings provided — pass holdings= for portfolio review automation.",
            "issues_recommendations": False,
            "recommendation_policy": "no_allocation_advice",
        }

    by_entity = {p.get("entity"): p for p in company_packs}
    by_display = {(p.get("display") or "").upper(): p for p in company_packs}
    holding_rows = []
    sector_exp: dict[str, int] = {}
    theme_exp: dict[str, int] = {}
    catalysts = []

    for h in holdings:
        key = h.upper()
        # resolve via display/entity
        p = by_display.get(key)
        if not p:
            from autonomous_research.util import resolve_ticker

            p = by_entity.get(resolve_ticker(h))
        if not p:
            holding_rows.append({"holding": key, "status": "not_covered", "research_required": True})
            continue
        oie = oie_of(p)
        kd = delta_of(p)
        graph = p.get("knowledge_graph") or {}
        sk = graph.get("sector_key") or ((p.get("memory") or {}).get("sector_history") or {}).get("sector_key") or "unknown"
        sector_exp[sk] = sector_exp.get(sk, 0) + 1
        for th in graph.get("themes") or []:
            theme_exp[th] = theme_exp.get(th, 0) + 1
        for c in oie.get("catalysts") or []:
            if c.get("importance") in {"High", "Medium"}:
                catalysts.append({"holding": p.get("display") or key, **{k: c.get(k) for k in ("name", "importance", "expected_window")}})

        holding_rows.append(
            {
                "holding": p.get("display") or key,
                "entity": p.get("entity"),
                "opportunity_score": oie.get("score"),
                "research_priority": oie.get("research_priority"),
                "delta_status": kd.get("status"),
                "opportunity_change": kd.get("summary") if kd.get("status") not in {None, "UNCHANGED"} else None,
                "risk_evolution": [b.get("title") for b in (oie.get("blockers") or [])[:3]],
                "why_now": oie.get("why_now"),
                "research_required": priority_rank(oie.get("research_priority")) <= 2
                or bool([b for b in (oie.get("blockers") or []) if b.get("severity") == "High"]),
            }
        )

    return {
        "ok": True,
        "as_of": now_iso(),
        "holdings": [h.upper() for h in holdings],
        "holding_changes": holding_rows,
        "opportunity_changes": [h for h in holding_rows if h.get("opportunity_change")],
        "risk_evolution": [
            {"holding": h.get("holding"), "risks": h.get("risk_evolution")}
            for h in holding_rows
            if h.get("risk_evolution")
        ],
        "macro_exposure": {"note": "Derived from sector/theme graph membership", "sectors": dict(sorted(sector_exp.items()))},
        "sector_exposure": dict(sorted(sector_exp.items())),
        "theme_exposure": dict(sorted(theme_exp.items())),
        "catalyst_exposure": catalysts,
        "portfolio_ops": {
            "urgency": (portfolio_ops or {}).get("urgency"),
            "expected_impact": (portfolio_ops or {}).get("expected_impact"),
        },
        "issues_recommendations": False,
        "recommendation_policy": "no_allocation_advice",
        "disclaimer": "Automated portfolio review for research attention — not an allocation recommendation.",
    }
