"""Risk Analyst — What can go wrong?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    cm = ctx.get("company_monitor") if isinstance(ctx.get("company_monitor"), dict) else {}
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    de = ctx.get("decision_engine") if isinstance(ctx.get("decision_engine"), dict) else {}
    layers = {str(l.get("id")): l for l in (de.get("layers") or []) if isinstance(l, dict)}
    risk_layer = layers.get("risk") or {}
    ail = ctx.get("intelligence_layer") if isinstance(ctx.get("intelligence_layer"), dict) else {}
    name = company_name(ctx)

    what = cm.get("what_changed") if isinstance(cm.get("what_changed"), dict) else cm
    business_risks = as_list(
        ca.get("key_risks")
        or (ca.get("investment_thesis") or {}).get("risks")
        or what.get("risks")
        or risk_layer.get("negative"),
        limit=6,
    )
    financial_risks = as_list((ca.get("financial_intelligence") or {}).get("what_deserves_monitoring"), limit=4)
    # Soft ACI — accounting / governance risk desk (no redesign)
    aci = ctx.get("accounting_intelligence") if isinstance(ctx.get("accounting_intelligence"), dict) else {}
    aci_desk = aci.get("desk") if isinstance(aci.get("desk"), dict) else {}
    accounting_risks = as_list(
        (aci.get("open_concerns") or aci_desk.get("open_concerns") or [])
        + (
            [f"Manipulation risk: {aci.get('manipulation_risk')}"]
            if aci.get("manipulation_risk") and aci.get("manipulation_risk") != "low"
            else []
        ),
        limit=4,
    )
    if not business_risks:
        business_risks = ["Execution miss", "Competitive intensity", "Regulatory change"]
    if not financial_risks:
        financial_risks = ["Earnings volatility", "Balance-sheet stress"]

    evidence = as_list(cm.get("alerts") or risk_layer.get("evidence") or ail.get("contradictory_evidence_ids"), limit=6)
    if aci.get("accounting_quality_score") is not None:
        evidence = [
            f"ACI quality {aci.get('accounting_quality_score')} · behaviour {aci.get('behaviour')}",
            *evidence,
        ][:6]
    if not evidence:
        evidence = ["Risk register from institutional monitoring", "Thesis invalidation conditions"]

    score = risk_layer.get("score")
    stance = "Bearish" if (isinstance(score, (int, float)) and float(score) < 50) or len(business_risks) >= 4 else "Neutral"
    if aci.get("manipulation_risk") == "high":
        stance = "Bearish"
    coverage = pick_confidence(score, cm.get("confidence"), default=0.57)

    return structured_opinion(
        role="risk",
        summary=f"{name}: downside is a function of business, financial, accounting, macro, execution, and valuation shocks.",
        strengths=as_list(what.get("monitor") or ["Active monitoring list in place"], limit=3),
        weaknesses=business_risks[:4],
        evidence=evidence,
        unanswered_questions=[
            "Which single risk, if realised, most impairs franchise returns?",
            "What leading indicator should force a thesis review?",
            "Are reported earnings cash-backed and free of material accounting concerns?",
        ],
        sections={
            "business_risks": business_risks,
            "financial_risks": financial_risks,
            "accounting_risks": accounting_risks or ["No ACI red flags in current soft slice"],
            "macro_risks": as_list(risk_layer.get("macro_risks") or ["Rate shock", "Growth slowdown"], limit=4),
            "execution_risks": as_list(what.get("execution_risks") or ["Delivery against guidance", "Ops complexity"], limit=4),
            "valuation_risks": as_list(["Multiple compression", "Expectations reset"], limit=4),
            "probability": risk_layer.get("reasoning") or "Severe impairment is moderate unless several risks coincide",
            "impact": "High-impact risks are those that impair franchise returns or capital",
            "monitoring": as_list(
                what.get("monitor")
                or ca.get("monitoring")
                or ["Next earnings", "Guidance", "Asset quality / margins", "Cash conversion / accruals"],
                limit=5,
            ),
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.5 + 0.05 * min(len(evidence), 4), default=0.55),
            "knowledge": coverage,
            "freshness": pick_confidence(cm.get("freshness"), default=0.6),
            "coverage": coverage,
        },
        score=float(score) if isinstance(score, (int, float)) else None,
        ctx=ctx,
    )
