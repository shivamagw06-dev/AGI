"""Ownership Analyst — Who owns this business?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    cid = ctx.get("company_dossier") if isinstance(ctx.get("company_dossier"), dict) else {}
    leo = ctx.get("live_evidence") if isinstance(ctx.get("live_evidence"), dict) else {}
    yfp = ctx.get("yahoo_enrichment") if isinstance(ctx.get("yahoo_enrichment"), dict) else {}
    share = (
        cid.get("shareholding")
        if isinstance(cid.get("shareholding"), dict)
        else cid.get("ownership")
        if isinstance(cid.get("ownership"), dict)
        else yfp.get("ownership")
        if isinstance(yfp.get("ownership"), dict)
        else {}
    )
    name = company_name(ctx)

    announcements = as_list(leo.get("announcements_used"), limit=6)
    evidence = [a for a in announcements if "share" in a.lower() or "holding" in a.lower()]
    evidence = evidence or announcements[:3] or [f"Shareholding disclosures for {name}"]

    trend = str(share.get("trend") or share.get("ownership_trend") or "")
    stance = "Bullish" if any(w in trend.lower() for w in ("rising", "stable", "align")) else "Neutral"
    if any(w in trend.lower() for w in ("falling", "pledge", "exit")):
        stance = "Bearish"

    coverage = pick_confidence(share.get("confidence"), default=0.5)
    return structured_opinion(
        role="ownership",
        summary=f"{name}: ownership structure and trends signal alignment and free-float dynamics.",
        strengths=as_list(
            [share.get("promoters") or share.get("promoter") or "Promoter holding under disclosure", share.get("institutions") or "Institutional ownership present"],
            limit=3,
        ),
        weaknesses=as_list([share.get("insiders") or "Insider activity windows deserve monitoring", "Sequential stake changes need confirmation"], limit=3),
        evidence=evidence,
        unanswered_questions=[
            "Are promoter and institutional stakes moving in the same direction?",
            "Is free float adequate for institutional sizing?",
        ],
        sections={
            "promoters": share.get("promoters") or share.get("promoter") or "Promoter holding under disclosure",
            "institutions": share.get("institutions") or share.get("institutional") or "Institutional ownership present in large-cap names",
            "mutual_funds": share.get("mutual_funds") or share.get("mf") or "Domestic mutual-fund participation",
            "fiis": share.get("fiis") or share.get("fii") or "Foreign institutional ownership",
            "diis": share.get("diis") or share.get("dii") or "Domestic institutional ownership",
            "insiders": share.get("insiders") or "Insider activity monitored around windows",
            "ownership_trend": trend or "Track sequential changes in promoter and institutional stakes",
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.45 + 0.08 * min(len(evidence), 3), default=0.48),
            "knowledge": coverage,
            "freshness": pick_confidence(leo.get("freshness_score"), default=0.5),
            "coverage": coverage,
        },
        ctx=ctx,
    )
