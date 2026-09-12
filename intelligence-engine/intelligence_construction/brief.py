"""Build a seamless institutional research brief from canonical AGI packages.

Consumes CID / Company Analysis / Monitor / KF / Academy / LEO / DVC / ECP / IRP.
Never mentions providers. Interpretive prose only — no raw dumps.
"""

from __future__ import annotations

import re
from typing import Any

from company_analysis.cid_bridge import ownership_snapshot
from intelligence_construction.cio_prose import (
    academy_from_company_analysis,
    academy_reasoning_bullets,
    business_intelligence_narrative,
    market_intelligence_pack,
    research_takeaways,
)
from intelligence_construction.flags import flags_dict, is_enabled
from intelligence_construction.schema import ARCHITECTURE_STATUS, IC_VERSION, PROGRAMME


def _txt(v: Any, limit: int = 420) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return s[:limit]


def _list(v: Any, limit: int = 6) -> list[str]:
    if not isinstance(v, list):
        return []
    out: list[str] = []
    for item in v:
        t = _txt(item, 280)
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def _ownership_narrative(cid: dict[str, Any]) -> str | None:
    own = ownership_snapshot(cid)
    bits: list[str] = []
    inst = own.get("institutions_percent")
    insider = own.get("insiders_percent")
    try:
        if inst is not None:
            iv = float(inst)
            if iv > 1.5:
                iv = iv  # already percent
            else:
                iv = iv * 100
            bits.append(
                f"Institutional ownership near {iv:.1f}% is a useful conviction signal and should be read alongside valuation and business developments."
            )
    except (TypeError, ValueError):
        pass
    try:
        if insider is not None:
            iv = float(insider)
            if iv <= 1.5:
                iv = iv * 100
            bits.append(
                f"Insider ownership around {iv:.1f}% warrants qualitative judgement — selling or buying only matters in context of price and strategy."
            )
    except (TypeError, ValueError):
        pass
    if own.get("ceo"):
        bits.append(f"Leadership context includes CEO {own['ceo']}.")
    return " ".join(bits) if bits else None


def _calendar_narrative(cid: dict[str, Any], company_monitor: dict[str, Any]) -> str | None:
    bits: list[str] = []
    anns = list(cid.get("announcements") or [])[:4]
    for a in anns:
        if not isinstance(a, dict):
            continue
        title = a.get("title") or a.get("headline") or a.get("type")
        if title:
            bits.append(str(title)[:160])
    changed = company_monitor.get("what_changed") if isinstance(company_monitor, dict) else {}
    if isinstance(changed, dict):
        for item in (changed.get("changes") or changed.get("items") or [])[:3]:
            if isinstance(item, dict) and item.get("detail"):
                bits.append(str(item["detail"])[:160])
            elif isinstance(item, str):
                bits.append(item[:160])
    if not bits:
        return None
    return "Upcoming / recent corporate calendar context: " + "; ".join(bits[:4]) + "."


def build_institutional_research_brief(
    *,
    query: str = "",
    ticker: str | None = None,
    cid: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    company_monitor: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    knowledge_foundation: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    data_validation: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    irp: dict[str, Any] | None = None,
    investment_office: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {
            "enabled": False,
            "programme": PROGRAMME,
            "version": IC_VERSION,
            "bypassed": True,
            "architecture_status": ARCHITECTURE_STATUS,
        }

    cid = cid if isinstance(cid, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cm = company_monitor if isinstance(company_monitor, dict) else {}
    irp = irp if isinstance(irp, dict) else {}
    academy = finance_academy if isinstance(finance_academy, dict) else {}
    kf = knowledge_foundation if isinstance(knowledge_foundation, dict) else {}
    leo = live_evidence if isinstance(live_evidence, dict) else {}
    dvc = data_validation if isinstance(data_validation, dict) else {}
    ecp = evidence_completion if isinstance(evidence_completion, dict) else {}
    io = investment_office if isinstance(investment_office, dict) else {}
    sif = sector_intelligence if isinstance(sector_intelligence, dict) else (ca.get("sector_intelligence") or {})

    identity = ca.get("identity") or cid.get("identity") or {}
    name = identity.get("company_name") or ticker or cid.get("ticker") or "the company"
    financial = ca.get("financial_intelligence") or {}
    valuation = ca.get("valuation_intelligence") or {}
    bq = ca.get("business_quality") or {}
    thesis = _txt(ca.get("investment_thesis") or (irp.get("reasoning") or {}).get("what_is_happening"))
    irp_brief = irp.get("institutional_briefing") if isinstance(irp.get("institutional_briefing"), dict) else {}

    business = business_intelligence_narrative(cid=cid, company_analysis=ca, sector_intelligence=sif)
    market = market_intelligence_pack(cid, ca)
    market_n = market.get("narrative")
    ownership_n = _ownership_narrative(cid)
    calendar_n = _calendar_narrative(cid, cm)
    financial_n = _txt(financial.get("narrative"), 600)
    valuation_n = _txt(valuation.get("narrative"), 600)
    bq_score = bq.get("business_quality_score")
    academy_bits = academy_reasoning_bullets(academy, limit=4) + academy_from_company_analysis(ca)
    academy_bits = list(dict.fromkeys([a for a in academy_bits if a]))[:5]

    why: list[str] = []
    if business.get("business_model"):
        why.append(business["business_model"])
    if business.get("competitive_advantages"):
        why.append(business["competitive_advantages"])
    if market_n:
        why.append(market_n)
    if financial_n:
        why.append(financial_n)
    if valuation_n:
        why.append(valuation_n)
    if ownership_n:
        why.append(ownership_n)
    for hint in academy_bits[:3]:
        if hint not in why:
            why.append(hint)
    for hint in (ca.get("ask_agi_hints") or [])[:3]:
        t = _txt(hint, 280)
        if t and t not in why and "readiness" not in t.lower() and "gate" not in t.lower():
            why.append(t)
    for hint in (cm.get("ask_agi_hints") or [])[:2]:
        t = _txt(hint, 260)
        if t and t not in why and "change(s)" not in t.lower():
            why.append(t)
    # Skip LEO/ECP/IO status hints — they read as pipeline reports, not research.
    _ = (leo, ecp, io, dvc, kf)
    if calendar_n:
        why.append(calendar_n)

    exec_bits = []
    if business.get("narrative"):
        exec_bits.append(business["narrative"].split(".")[0] + ".")
    if thesis and "not a recommendation" not in thesis.lower() and "key applied lenses" not in thesis.lower():
        exec_bits.append(thesis)
    elif market_n:
        exec_bits.append(market_n.split(".")[0] + ".")
    if financial_n:
        exec_bits.append(financial_n.split(".")[0] + ".")
    if valuation_n:
        exec_bits.append(valuation_n.split(".")[0] + ".")
    if academy_bits:
        exec_bits.append(academy_bits[0])
    executive = " ".join(exec_bits)[:900] if exec_bits else (
        f"{name} requires a full institutional read across business model, competitive position, "
        "sector structure, financial quality and valuation — even where some statement fields remain incomplete."
    )

    key_drivers = _list(
        (irp_brief.get("key_drivers") or [])
        + _list(financial.get("what_improved"), 3)
        + _list((ca.get("catalysts") or []), 3),
        8,
    )
    # Humanise snake_case driver tokens
    key_drivers = [d.replace("_", " ") if re.fullmatch(r"[a-z]+(?:_[a-z0-9]+)+", d) else d for d in key_drivers]
    risks = _list((ca.get("risks") or []) + _list((irp.get("reasoning") or {}).get("risks"), 4), 6)
    catalysts = _list((ca.get("catalysts") or []) + _list((irp.get("reasoning") or {}).get("catalysts"), 4), 6)
    takeaways = research_takeaways(
        business=business,
        market=market,
        financial_n=financial_n,
        valuation_n=valuation_n,
        academy_bits=academy_bits,
        risks=risks,
    )

    sections = {
        "market_performance": {
            "narrative": market_n,
            "snapshot": market.get("snapshot") or {},
            "cards": market.get("cards") or [],
            "momentum": market.get("momentum"),
        },
        "business_intelligence": business,
        "business_quality": {
            "score": bq_score,
            "grade": bq.get("grade"),
            "narrative": business.get("competitive_advantages")
            or _txt(bq.get("narrative") or bq.get("summary"), 400),
        },
        "financial_intelligence": {
            "narrative": financial_n or business.get("operating_metrics"),
            "coverage_pct": financial.get("coverage_pct"),
            "what_improved": [str(x).replace("_", " ") for x in (financial.get("what_improved") or [])],
            "what_deteriorated": [str(x).replace("_", " ") for x in (financial.get("what_deteriorated") or [])],
        },
        "valuation": {
            "narrative": valuation_n
            or (
                f"Valuation for {name} should be framed against growth durability and competitive position — "
                "multiples alone are incomplete without that context."
            ),
            "current_pe": valuation.get("current_pe"),
            "forward_pe": valuation.get("forward_pe"),
            "pb": valuation.get("pb"),
            "coverage_pct": valuation.get("coverage_pct"),
        },
        "ownership": {"narrative": ownership_n, "snapshot": ownership_snapshot(cid)},
        "capital_allocation": {
            "signal": financial.get("capital_allocation"),
            "dividend_yield": valuation.get("dividend_yield"),
        },
        "what_changed": cm.get("what_changed") or ca.get("what_changed") or {},
        "calendar": {"narrative": calendar_n},
        "academy": {
            "hints": academy_bits,
            "reasoning": academy_bits,
        },
        "sector_intelligence": {
            "narrative": business.get("industry_structure"),
        },
        "research_takeaways": takeaways,
        "risks": risks,
        "catalysts": catalysts,
    }

    return {
        "enabled": True,
        "programme": PROGRAMME,
        "version": IC_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "flags": flags_dict(),
        "query": query,
        "ticker": (ticker or identity.get("ticker") or cid.get("ticker") or None),
        "company_name": name,
        "executive_brief": executive,
        "sections": sections,
        "answer_enrichment": {
            "executive_summary": executive,
            "why_bullets": why[:12],
            "valuation_perspective": valuation_n or _txt(irp_brief.get("valuation_perspective"), 400),
            "key_drivers": key_drivers,
            "current_outlook": _txt(irp_brief.get("current_outlook") or thesis, 400)
            if thesis and "insufficient" not in str(irp_brief.get("current_outlook") or "").lower()
            else (business.get("long_term_growth") or executive)[:400],
            "risks": risks,
            "catalysts": catalysts,
            "business_intelligence": business,
            "market_intelligence": market,
            "research_takeaways": takeaways,
            "academy_reasoning": academy_bits,
        },
        "answer_policy": "cio_equity_research_note",
        "never_expose_providers": True,
        "never_expose_framework_names": True,
    }
