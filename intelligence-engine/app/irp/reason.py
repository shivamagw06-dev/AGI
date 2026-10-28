"""Steps 8–12 — Institutional reasoning package (before answer generation)."""

from __future__ import annotations

import re
from typing import Any

from app.irp.models import (
    ContradictionNote,
    InstitutionalReasoning,
    RankedEvidenceItem,
    ResolvedEntityPack,
)
from app.ui.iax import normalize_stance, synthesize_thesis_points, stance_from_text


def build_institutional_reasoning(
    question: str,
    *,
    intent: str,
    domain: str,
    entities: ResolvedEntityPack,
    ranked: list[RankedEvidenceItem],
    contradictions: list[ContradictionNote],
    house_view: dict[str, Any] | None,
    rsp: dict[str, Any] | None,
) -> InstitutionalReasoning:
    house = house_view or {}
    cv = house.get("current_view") if isinstance(house.get("current_view"), dict) else {}
    thesis = str(
        house.get("thesis")
        or house.get("summary")
        or (cv.get("thesis") if isinstance(cv, dict) else "")
        or (ranked[0].snippet if ranked else "")
        or ""
    ).strip()
    thesis = re.sub(r"\s+", " ", thesis.replace("&amp;", "&"))

    synth_pts = synthesize_thesis_points(thesis)
    bull = list(house.get("bull_case") or (cv.get("bull_case") if isinstance(cv, dict) else []) or [])
    bear = list(house.get("bear_case") or (cv.get("bear_case") if isinstance(cv, dict) else []) or [])
    risks = list(house.get("risks") or house.get("failed_assumptions") or [])
    catalysts = list(house.get("catalysts") or house.get("catalysts_occurred") or [])
    if not bull:
        bull = synth_pts["bull_case"]
    if not bear:
        bear = synth_pts["bear_case"]
    if not risks:
        risks = synth_pts["risks"] or _default_risks(entities, thesis)
    if not catalysts:
        catalysts = synth_pts["catalysts"] or _default_catalysts(entities, thesis)

    # RSP soft enrichment
    rsp = rsp or {}
    rsp_synth = rsp.get("synthesis") if isinstance(rsp.get("synthesis"), dict) else rsp
    if isinstance(rsp_synth, dict):
        if not bull:
            bull = [str(x) for x in (rsp_synth.get("bull_case") or [])][:6]
        if not bear:
            bear = [str(x) for x in (rsp_synth.get("bear_case") or [])][:6]
        if not risks:
            risks = [str(x) for x in (rsp_synth.get("risks") or [])][:6]
        if not catalysts:
            catalysts = [str(x) for x in (rsp_synth.get("catalysts") or [])][:6]

    stance = normalize_stance(
        house.get("stance")
        or house.get("current_view_label")
        or house.get("label")
        or {"thesis": thesis, "bull_case": bull, "bear_case": bear}
    )
    if stance == "Neutral" and thesis:
        stance = stance_from_text(thesis)

    conf = house.get("confidence") or house.get("research_confidence")
    if conf is None:
        conf = rsp.get("confidence")
    if conf is None and ranked:
        conf = sum(r.confidence for r in ranked[:5]) / max(1, min(5, len(ranked)))
    conf_f = float(conf or 0.55)
    if conf_f > 1:
        conf_f = conf_f / 100.0

    supports = [
        f"{r.title}: {r.snippet[:160]}".strip(": ")
        for r in ranked[:4]
        if r.title or r.snippet
    ]
    contradicts = [c.summary for c in contradictions[:4]]

    what_changed = ""
    if isinstance(house.get("what_changed"), list) and house["what_changed"]:
        what_changed = str(house["what_changed"][0])
    elif isinstance(house.get("thesis_evolution"), list) and house["thesis_evolution"]:
        what_changed = str(house["thesis_evolution"][0])
    else:
        what_changed = "Latest sector/company notes update growth visibility and demand assumptions."

    leaders = [f"{c.get('ticker')} — {c.get('name')}" for c in (entities.companies or [])[:8]]
    macro = list(entities.macro_drivers or [])
    sector_drivers = _sector_drivers(thesis, entities)

    outlook = _outlook_sentence(stance, thesis, entities)
    why = _why_sentence(thesis, entities, domain)
    why_matters = (
        f"Positioning across {entities.sector_label or entities.primary_ticker or 'the subject'} "
        f"affects earnings, multiples, and relative performance versus the broader market."
    )

    uncertainties = [
        "Near-term demand conversion timing remains uncertain.",
        "AI productivity impact on pricing/volumes is still forming.",
    ]
    if contradictions:
        uncertainties.append("Material disagreement remains across sourced research opinions.")

    valuation = ""
    if isinstance(house.get("valuation"), str) and house.get("valuation"):
        valuation = str(house["valuation"])[:300]
    else:
        valuation = (
            "Valuation lens: prefer relative multiples versus history and growth visibility; "
            "no fabricated target prices without sourced evidence."
        )

    historical = ""
    hist = house.get("historical_views") or []
    if isinstance(hist, list) and len(hist) >= 2:
        historical = "Multiple AGI research versions exist — compare thesis evolution in the timeline."
    else:
        historical = "Limited historical AGI versions on file; treat the latest note as the current anchor."

    neutral = []
    if stance == "Neutral":
        neutral = ["Stay selective; wait for clearer demand/guidance catalysts before raising conviction."]
    elif stance == "Bearish":
        neutral = ["A neutral path requires stabilising QoQ growth and firmer large-deal conversion."]
    else:
        neutral = ["A neutral path would require growth fading back toward muted levels."]

    return InstitutionalReasoning(
        what_is_happening=thesis[:500] or outlook,
        why=why,
        what_changed=what_changed[:400],
        why_it_matters=why_matters,
        supports=supports,
        contradicts=contradicts,
        confidence=round(conf_f, 4),
        uncertainties=uncertainties[:5],
        stance=stance,
        outlook=outlook,
        key_drivers=sector_drivers[:6] or macro[:6],
        bull_case=[str(x) for x in bull][:6],
        bear_case=[str(x) for x in bear][:6],
        neutral_case=neutral,
        risks=[str(x) for x in risks][:6],
        catalysts=[str(x) for x in catalysts][:6],
        valuation_perspective=valuation,
        macro_drivers=macro[:6],
        sector_drivers=sector_drivers[:6],
        company_leaders=leaders,
        historical_comparison=historical,
    )


def build_sector_intelligence(entities: ResolvedEntityPack, reasoning: InstitutionalReasoning) -> dict[str, Any]:
    if not entities.sector_key and not entities.sector_label:
        return {}
    return {
        "sector_overview": entities.sector_label or entities.sector,
        "top_companies": entities.companies[:10],
        "demand_drivers": reasoning.sector_drivers or reasoning.key_drivers,
        "macro_drivers": reasoning.macro_drivers,
        "current_agi_view": reasoning.stance,
        "outlook": reasoning.outlook,
        "key_risks": reasoning.risks,
        "future_catalysts": reasoning.catalysts,
        "competitive_landscape": [
            "Tier-1 scale franchises vs mid-tier specialists",
            "AI/cloud mix and discretionary spend exposure",
        ],
        "countries": entities.countries,
        "themes": entities.themes,
        "currencies": entities.currencies,
    }


def build_company_intelligence(entities: ResolvedEntityPack, reasoning: InstitutionalReasoning) -> dict[str, Any]:
    if not entities.primary_ticker:
        return {}
    return {
        "ticker": entities.primary_ticker,
        "current_agi_view": reasoning.stance,
        "outlook": reasoning.outlook,
        "key_drivers": reasoning.key_drivers,
        "risks": reasoning.risks,
        "catalysts": reasoning.catalysts,
        "valuation_perspective": reasoning.valuation_perspective,
        "related_peers": [c.get("ticker") for c in entities.companies if c.get("ticker") != entities.primary_ticker][:8],
    }


def build_institutional_briefing(reasoning: InstitutionalReasoning, *, question: str) -> dict[str, Any]:
    return {
        "executive_summary": (
            f"{reasoning.stance} view. {reasoning.outlook} "
            f"Confidence {round(reasoning.confidence * 100)}%."
        ).strip(),
        "current_outlook": reasoning.outlook,
        "key_drivers": reasoning.key_drivers,
        "bull_case": reasoning.bull_case,
        "bear_case": reasoning.bear_case,
        "neutral_case": reasoning.neutral_case,
        "risks": reasoning.risks,
        "catalysts": reasoning.catalysts,
        "valuation_perspective": reasoning.valuation_perspective,
        "macro_drivers": reasoning.macro_drivers,
        "sector_drivers": reasoning.sector_drivers,
        "company_leaders": reasoning.company_leaders,
        "historical_comparison": reasoning.historical_comparison,
        "what_is_happening": reasoning.what_is_happening,
        "why": reasoning.why,
        "what_changed": reasoning.what_changed,
        "why_it_matters": reasoning.why_it_matters,
        "supports": reasoning.supports,
        "contradicts": reasoning.contradicts,
        "uncertainties": reasoning.uncertainties,
        "question": question,
    }


def _outlook_sentence(stance: str, thesis: str, entities: ResolvedEntityPack) -> str:
    subject = entities.sector_label or entities.primary_ticker or "the subject"
    if stance == "Bearish":
        return (
            f"{subject}: near-term outlook remains cautious on growth visibility, "
            f"deal conversion, and AI-related productivity/pricing pressure."
        )
    if stance == "Bullish":
        return f"{subject}: outlook is constructive on demand recovery and earnings momentum."
    return f"{subject}: outlook is balanced — selective opportunities with still-muted visibility."


def _why_sentence(thesis: str, entities: ResolvedEntityPack, domain: str) -> str:
    if thesis:
        return thesis[:240]
    if domain == "sector":
        return f"Sector question resolved to {entities.sector_label or 'sector universe'} with mapped leaders and macro drivers."
    if entities.primary_ticker:
        return f"Company question resolved to {entities.primary_ticker} with AGI / broker evidence ranked by priority."
    return "Intent and entities were resolved before retrieval to keep the evidence pack institutional."


def _sector_drivers(thesis: str, entities: ResolvedEntityPack) -> list[str]:
    drivers = list(entities.macro_drivers or [])
    low = (thesis or "").lower()
    if "deal" in low:
        drivers.append("Large-deal conversion / pipeline timing")
    if "ai" in low or "productivity" in low:
        drivers.append("AI productivity impact on pricing and volumes")
    if "0% qoq" in low or "muted" in low:
        drivers.append("Muted sequential revenue growth")
    # unique
    out: list[str] = []
    seen: set[str] = set()
    for d in drivers:
        k = d.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(d)
    return out


def _default_risks(entities: ResolvedEntityPack, thesis: str) -> list[str]:
    risks = []
    if entities.sector_key == "INDIA_IT":
        risks = [
            "US/Europe client budget freezes",
            "Slower large-deal conversion",
            "AI-led pricing / productivity pressure",
        ]
    elif entities.primary_ticker:
        risks = ["Earnings miss versus expectations", "Multiple compression on weaker guidance"]
    if "macro" in (thesis or "").lower():
        risks.append("Macro demand softness")
    return risks[:6]


def _default_catalysts(entities: ResolvedEntityPack, thesis: str) -> list[str]:
    if entities.sector_key == "INDIA_IT":
        return [
            "Stabilising QoQ growth / FY guidance upgrades",
            "Large-deal wins in BFSI or manufacturing",
            "Clearer monetisation path for GenAI programmes",
        ]
    if entities.primary_ticker:
        return ["Next earnings print", "Management commentary on demand"]
    return ["Upcoming data / earnings catalysts"]
