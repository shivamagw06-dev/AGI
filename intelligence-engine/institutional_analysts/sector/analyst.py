"""Sector Analyst — Is the industry attractive?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    sector = ctx.get("sector_intelligence") if isinstance(ctx.get("sector_intelligence"), dict) else {}
    academy = ctx.get("finance_academy") if isinstance(ctx.get("finance_academy"), dict) else {}
    kf = ctx.get("knowledge_foundation") if isinstance(ctx.get("knowledge_foundation"), dict) else {}
    sif = sector.get("sif") if isinstance(sector.get("sif"), dict) else sector
    name = company_name(ctx)
    sector_id = str(sector.get("sector_id") or sif.get("sector_id") or "the sector")

    growth = str(sif.get("growth") or sector.get("growth") or "")
    stance = "Bullish" if any(w in growth.lower() for w in ("attract", "strong", "expand")) else "Neutral"
    if any(w in growth.lower() for w in ("structur", "headwind", "weak")):
        stance = "Bearish"

    evidence = []
    evidence.extend(as_list(sif.get("priority_metrics") or sector.get("priority_metrics"), limit=4))
    evidence.extend(as_list(academy.get("courses") or academy.get("concepts"), limit=2))
    evidence.extend(as_list(kf.get("hits") or kf.get("themes"), limit=2))

    coverage = pick_confidence((sector.get("detection") or {}).get("confidence"), sif.get("confidence"), default=0.6)
    return structured_opinion(
        role="sector",
        summary=f"{name} operates within {sector_id}: industry structure and KPIs set the opportunity set.",
        strengths=as_list(
            [sif.get("structure") or sector.get("structure") or f"{sector_id} structure supports scaled operators", growth or "Sector growth assumptions under review"],
            limit=4,
        ),
        weaknesses=as_list([sif.get("competition") or "Competitive intensity can compress returns", sif.get("regulation") or "Regulation remains a first-order variable"], limit=4),
        evidence=evidence or [f"Sector framing for {sector_id}"],
        unanswered_questions=[
            "Is sector growth mid-cycle or late-cycle?",
            "Which KPIs best discriminate winners from the pack?",
        ],
        sections={
            "industry_structure": sif.get("structure") or sector.get("structure") or f"{sector_id} competitive structure shapes returns",
            "competition": sif.get("competition") or sector.get("peers") or "Intensity of rivalry and substitutes matter for margins",
            "sector_growth": growth or "Mid-cycle growth assumptions should be evidence-led",
            "sector_kpis": sif.get("priority_metrics") or sector.get("priority_metrics") or ["Growth", "Margins", "Returns", "Asset quality"],
            "demand": sif.get("demand") or "Demand linked to cycle, policy, and spend",
            "supply": sif.get("supply") or "Supply/capacity and competitive entry affect pricing",
            "technology": sif.get("technology") or "Technology shifts can reset cost curves and distribution",
            "regulation": sif.get("regulation") or "Regulatory stance is a first-order sector variable",
            "leading_companies": sif.get("leaders") or sector.get("leaders") or ["Peer leaders define the quality bar"],
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.5 + 0.06 * min(len(evidence), 5), default=0.55),
            "knowledge": coverage,
            "freshness": 0.58,
            "coverage": coverage,
        },
        ctx=ctx,
    )
