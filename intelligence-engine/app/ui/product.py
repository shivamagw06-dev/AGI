"""AGI Product V1 helpers — discovery, prediction centre, research freshness (no engines)."""

from __future__ import annotations

from typing import Any

from app.ui.iax import enrich_timeline, house_view_card, knowledge_graph_view, normalize_stance
from app.ui.questions import follow_up_questions
from app.ui.sanitize import pick_label, pick_number, scrub, scrub_text


def discovery_pack(
    *,
    companies: list[str] | None = None,
    themes: list[str] | None = None,
    sectors: list[str] | None = None,
    research: list[dict[str, Any]] | None = None,
    questions: list[str] | None = None,
    popular: list[str] | None = None,
) -> dict[str, Any]:
    """Never let the user hit a dead end."""
    return {
        "related_companies": [str(c).upper() for c in (companies or []) if c][:8],
        "related_themes": [str(t) for t in (themes or []) if t][:8],
        "related_sectors": [str(s) for s in (sectors or []) if s][:6],
        "related_research": scrub(research or [])[:8],
        "related_questions": [str(q) for q in (questions or []) if q][:6],
        "popular_questions": [str(q) for q in (popular or []) if q][:6],
        "trending_topics": [str(t) for t in (themes or companies or [])[:6]],
    }


def prediction_row(raw: dict[str, Any] | None, *, ticker: str | None = None) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    row = scrub(raw)
    if not isinstance(row, dict):
        return None
    status = (
        row.get("status")
        or row.get("outcome")
        or row.get("result")
        or ("open" if not row.get("resolved_at") else "resolved")
    )
    return {
        "id": row.get("id") or row.get("prediction_id") or f"{ticker or 'PRED'}-{row.get('predicted_at') or row.get('as_of')}",
        "ticker": str(row.get("ticker") or ticker or "").upper() or None,
        "publication_date": row.get("predicted_at") or row.get("as_of") or row.get("published_at"),
        "target_horizon": row.get("horizon") or row.get("target_horizon") or "medium-term",
        "current_status": scrub_text(str(status)),
        "current_return": row.get("current_return") or row.get("return") or row.get("realized_return"),
        "supporting_research": scrub(row.get("supporting_research") or row.get("evidence") or [])[:6],
        "updates": scrub(row.get("updates") or [])[:6],
        "outcome": scrub_text(str(row.get("outcome"))) if row.get("outcome") is not None else None,
        "confidence": pick_number(row, "confidence"),
        "thesis": scrub_text(row.get("thesis") or row.get("summary") or row.get("label")),
        "target": row.get("target") or row.get("target_price"),
        "sector": row.get("sector"),
        "theme": row.get("theme"),
    }


def accuracy_summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [p for p in predictions if isinstance(p, dict)]
    if not rows:
        return {
            "house_view_accuracy": None,
            "sector_accuracy": {},
            "theme_accuracy": {},
            "prediction_success": None,
            "historical_performance": {"n": 0, "hit_rate": None},
            "n": 0,
        }
    resolved = [
        p
        for p in rows
        if str(p.get("current_status") or "").lower() in {"resolved", "hit", "miss", "success", "fail"}
        or p.get("outcome")
    ]
    hits = 0
    for p in resolved:
        out = str(p.get("outcome") or p.get("current_status") or "").lower()
        if any(x in out for x in ("hit", "success", "correct", "win")):
            hits += 1
    hit_rate = (hits / len(resolved)) if resolved else None

    sector_acc: dict[str, dict[str, Any]] = {}
    theme_acc: dict[str, dict[str, Any]] = {}
    for p in rows:
        sec = p.get("sector")
        th = p.get("theme")
        if sec:
            sector_acc.setdefault(str(sec), {"n": 0})
            sector_acc[str(sec)]["n"] += 1
        if th:
            theme_acc.setdefault(str(th), {"n": 0})
            theme_acc[str(th)]["n"] += 1

    return {
        "house_view_accuracy": hit_rate,
        "sector_accuracy": sector_acc,
        "theme_accuracy": theme_acc,
        "prediction_success": hit_rate,
        "historical_performance": {"n": len(rows), "resolved": len(resolved), "hit_rate": hit_rate},
        "n": len(rows),
    }


def thesis_status(*, house: dict[str, Any] | None, published_view: str | None = None) -> dict[str, Any]:
    house = house or {}
    current = normalize_stance(house.get("current_view") or house.get("stance") or house.get("label"))
    prior = normalize_stance(published_view) if published_view else None
    holds = True
    if prior and prior != current and prior != "Neutral":
        holds = current == prior
    changed = list(house.get("thesis_evolution") or house.get("changed_assumptions") or [])[:6]
    return {
        "current_stance": current,
        "published_stance": prior,
        "thesis_still_holds": holds if prior else None,
        "whats_changed_since_publication": [scrub_text(str(x)) for x in changed],
        "summary": (
            "Original thesis still aligned with current house view."
            if holds
            else "House view has evolved since publication — review evidence."
        ),
    }


def enrichment_meta(
    *,
    last_updated: Any = None,
    freshness_score: Any = None,
    evidence_count: int = 0,
    research_count: int = 0,
) -> dict[str, Any]:
    score = None
    try:
        if freshness_score is not None:
            score = float(freshness_score)
    except (TypeError, ValueError):
        score = None
    if score is None:
        indicator = "unknown"
    elif score >= 0.7:
        indicator = "fresh"
    elif score >= 0.4:
        indicator = "aging"
    else:
        indicator = "stale"
    return {
        "last_updated": str(last_updated) if last_updated else None,
        "freshness_score": score,
        "freshness_indicator": indicator,
        "evidence_count": int(evidence_count or 0),
        "research_count": int(research_count or 0),
    }


def theme_intelligence(
    *,
    theme_id: str,
    thesis: str | None,
    companies: list[str],
    risks: list[str],
    catalysts: list[str],
    research: list[dict[str, Any]],
    house: dict[str, Any] | None,
    graph: dict[str, Any] | None,
    timeline: list[dict[str, Any]],
    macro_themes: list[str] | None = None,
) -> dict[str, Any]:
    hv = house_view_card(house, pick_number(house or {}, "confidence"))
    kg = knowledge_graph_view(graph, companies[0] if companies else None)
    qs = follow_up_questions(
        question=f"What is AGI's view on {theme_id}?",
        intent="theme",
        related_companies=companies,
        related_themes=[theme_id] + list(macro_themes or []),
        house_label=hv.get("stance"),
        risks=risks,
        catalysts=catalysts,
        knowledge_graph=kg,
        recent_research_titles=[str(r.get("title")) for r in research[:3] if isinstance(r, dict)],
    )
    return {
        "confidence": hv.get("confidence"),
        "stance": hv.get("stance"),
        "related_macro": list(macro_themes or kg.get("buckets", {}).get("macro_themes") or [])[:8],
        "knowledge_graph": kg,
        "research_timeline": enrich_timeline(timeline),
        "follow_up_questions": qs,
        "discovery": discovery_pack(
            companies=companies,
            themes=[theme_id] + list(macro_themes or []),
            research=research,
            questions=qs,
        ),
        "product_meta": enrichment_meta(
            last_updated=(house or {}).get("updated_at") if house else None,
            freshness_score=(house or {}).get("freshness") if house else None,
            evidence_count=len(research),
            research_count=len(research),
        ),
    }


def sector_intelligence(
    *,
    sector_id: str,
    health: str | None,
    leaders: list[str],
    laggards: list[str],
    research: list[dict[str, Any]],
    valuation: dict[str, Any] | None,
    risks: list[str] | None = None,
    opportunities: list[str] | None = None,
    macro_drivers: list[str] | None = None,
    timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    risks = risks or []
    opportunities = opportunities or [
        f"Leaders in {sector_id} show relatively stronger institutional coverage.",
    ]
    if leaders and not opportunities:
        opportunities = [f"Focus coverage on {leaders[0]} relative to sector peers."]
    macro_drivers = macro_drivers or []
    qs = follow_up_questions(
        question=f"What is AGI's outlook for {sector_id}?",
        intent="sector",
        related_companies=leaders + laggards,
        related_themes=[sector_id],
        house_label=None,
        risks=risks,
        catalysts=opportunities,
    )
    return {
        "current_outlook": health or "Under review",
        "current_opportunities": [scrub_text(str(x)) for x in opportunities][:8],
        "current_risks": [scrub_text(str(x)) for x in risks][:8],
        "macro_drivers": [scrub_text(str(x)) for x in macro_drivers][:8],
        "sector_timeline": enrich_timeline(timeline or research),
        "valuation_summary": {
            "label": pick_label(valuation, "label", "status") if isinstance(valuation, dict) else None,
            "detail": scrub(valuation) if isinstance(valuation, dict) else {},
        },
        "follow_up_questions": qs,
        "discovery": discovery_pack(
            companies=leaders + laggards,
            sectors=[sector_id],
            research=research,
            questions=qs,
        ),
        "product_meta": enrichment_meta(
            evidence_count=len(research),
            research_count=len(research),
        ),
    }


def macro_intelligence(
    *,
    regime: dict[str, Any] | None,
    risk: dict[str, Any] | None,
    events: list[dict[str, Any]],
    research: list[dict[str, Any]],
    themes: list[str],
    related_companies: list[str] | None = None,
) -> dict[str, Any]:
    regime = regime if isinstance(regime, dict) else {}
    risk = risk if isinstance(risk, dict) else {}
    label = pick_label(regime, "regime", "label") or "Unavailable"
    risk_label = pick_label(risk, "risk_level", "label") or "Unavailable"
    what = f"Market regime is {label} with risk backdrop {risk_label}."
    why = scrub_text(str(regime.get("summary") or regime.get("explanation") or "Regime inferred from institutional market context."))
    beneficiaries = themes[:4] or ["Rate-sensitive financials" if "risk" in label.lower() else "Quality compounders"]
    losers = ["High-beta cyclicals"] if "risk" in str(risk_label).lower() else ["Crowded momentum sleeves"]
    qs = follow_up_questions(
        question="What is AGI's current macro view?",
        intent="macro",
        related_companies=related_companies or [],
        related_themes=themes,
        house_label=label,
    )
    return {
        "what_happened": what,
        "why": why,
        "who_benefits": [scrub_text(str(x)) for x in beneficiaries],
        "who_loses": [scrub_text(str(x)) for x in losers],
        "how_view_changed": scrub_text(str(regime.get("change") or "Compare with previous briefing in What's Changed.")),
        "related_research": research[:8],
        "related_companies": [str(c).upper() for c in (related_companies or [])][:8],
        "related_themes": themes[:8],
        "event_briefs": [
            {
                "title": scrub_text(e.get("title") or e.get("name")),
                "what_happened": scrub_text(e.get("summary") or e.get("title")),
                "why": scrub_text(e.get("why") or "Macro event in the institutional calendar."),
                "who_benefits": themes[:3],
                "who_loses": [],
            }
            for e in events[:8]
            if isinstance(e, dict)
        ],
        "follow_up_questions": qs,
        "discovery": discovery_pack(
            companies=related_companies,
            themes=themes,
            research=research,
            questions=qs,
        ),
    }
