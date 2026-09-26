"""P6.2 Autonomous Research Generator — analyst-ready evidence-backed drafts."""

from __future__ import annotations

from typing import Any

from autonomous_research.util import as_float, delta_of, now_iso, oie_of


def generate_research_pack(
    company_pack: dict[str, Any],
    *,
    research_type: str | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not company_pack.get("ok"):
        return {
            "ok": False,
            "error": "company_pack_unavailable",
            "issues_recommendations": False,
        }

    oie = oie_of(company_pack)
    kd = delta_of(company_pack)
    mem = company_pack.get("memory") if isinstance(company_pack.get("memory"), dict) else {}
    graph = company_pack.get("knowledge_graph") if isinstance(company_pack.get("knowledge_graph"), dict) else {}
    rtype = research_type or (plan or {}).get("research_type") or "company_update"
    entity = company_pack.get("entity")
    display = company_pack.get("display") or entity

    sections = [
        _section(
            "summary",
            f"{display} — {rtype.replace('_', ' ').title()}",
            oie.get("why_now") or "Compiled opportunity context available for analyst review.",
            [
                {"source": "opportunity_intelligence.why_now", "value": oie.get("why_now")},
                {"source": "opportunity_intelligence.score", "value": oie.get("score")},
            ],
        ),
        _section(
            "financial_context",
            "Financial momentum",
            _fin_text(mem),
            [{"source": "company_memory.financial_history", "value": (mem.get("financial_history") or {}).get("available")}],
        ),
        _section(
            "ownership_context",
            "Ownership momentum",
            _own_text(mem),
            [{"source": "company_memory.ownership_history", "value": (mem.get("ownership_history") or {}).get("latest")}],
        ),
        _section(
            "valuation_context",
            "Valuation backdrop",
            _val_text(mem, oie),
            [{"source": "company_memory.valuation_history", "value": (mem.get("valuation_history") or {}).get("stance")}],
        ),
        _section(
            "knowledge_delta",
            "What changed",
            kd.get("summary") or "No material Knowledge Delta versus prior memory.",
            [{"source": "knowledge_delta_engine", "value": kd}],
        ),
        _section(
            "graph_context",
            "Relationship context",
            _graph_text(graph),
            [{"source": "investment_knowledge_graph", "value": {"peers": graph.get("peers"), "themes": graph.get("themes")}}],
        ),
        _section(
            "catalysts",
            "Upcoming / recent catalysts",
            _list_text([c.get("name") for c in (oie.get("catalysts") or [])], empty="No high-signal catalysts in pack."),
            [{"source": "opportunity_intelligence.catalysts", "value": oie.get("catalysts")}],
        ),
        _section(
            "blockers_and_risks",
            "Research blockers",
            _list_text([b.get("title") for b in (oie.get("blockers") or [])], empty="No high-severity blockers flagged."),
            [{"source": "opportunity_intelligence.blockers", "value": oie.get("blockers")}],
        ),
        _section(
            "analyst_actions",
            "Suggested analyst review focus",
            _actions(rtype, oie, kd),
            [{"source": "autonomous_research.planner", "value": plan or {"research_type": rtype}}],
        ),
    ]

    citations = []
    for s in sections:
        for e in s.get("evidence") or []:
            citations.append({"section": s["id"], "source": e.get("source")})

    return {
        "ok": True,
        "draft": True,
        "governance_status": "pending_analyst_review",
        "approved_for_publication": False,
        "company": display,
        "entity": entity,
        "research_type": rtype,
        "priority": oie.get("research_priority") or (plan or {}).get("priority"),
        "opportunity_score": oie.get("score"),
        "generated_at": now_iso(),
        "memory_version": mem.get("memory_version") or (oie.get("freshness") or {}).get("memory_version"),
        "delta_status": kd.get("status"),
        "sections": sections,
        "citations": citations,
        "confidence": as_float(oie.get("confidence")),
        "issues_recommendations": False,
        "recommendation_policy": "draft_for_analyst_review_only",
        "disclaimer": "Autonomous draft — not an investment recommendation; subject to CID/DE/governance.",
    }


def generate_for_plans(
    company_packs: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> dict[str, Any]:
    by_entity = {p.get("entity"): p for p in company_packs}
    by_display = {(p.get("display") or "").upper(): p for p in company_packs}
    drafts = []
    for plan in plans[: max(1, min(int(limit), 50))]:
        ent = plan.get("entity")
        p = by_entity.get(ent) or by_display.get((plan.get("company") or "").upper())
        if not p:
            continue
        drafts.append(generate_research_pack(p, research_type=plan.get("research_type"), plan=plan))
    return {"n": len(drafts), "drafts": drafts, "approved_for_publication": False}


def _section(sid: str, title: str, body: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": sid,
        "title": title,
        "body": body,
        "evidence": evidence,
        "evidence_backed": bool(evidence),
    }


def _fin_text(mem: dict[str, Any]) -> str:
    fh = mem.get("financial_history") or {}
    if not fh.get("available"):
        return "Financial history not available in compiled memory."
    rev = (fh.get("revenue") or {}).get("yoy")
    pat = (fh.get("pat") or {}).get("yoy")
    bits = []
    if rev is not None:
        bits.append(f"Revenue YoY {rev}%")
    if pat is not None:
        bits.append(f"PAT YoY {pat}%")
    return "; ".join(bits) if bits else "Financial history present; key growth fields sparse."


def _own_text(mem: dict[str, Any]) -> str:
    oh = mem.get("ownership_history") or {}
    trends = oh.get("trends") or {}
    bits = []
    for k in ("fii", "dii", "promoter", "mutual_funds"):
        d = (trends.get(k) or {}).get("direction")
        if d:
            bits.append(f"{k.upper()} {d}")
    return "; ".join(bits) if bits else "Ownership trends not material in compiled memory."


def _val_text(mem: dict[str, Any], oie: dict[str, Any]) -> str:
    vh = mem.get("valuation_history") or {}
    stance = vh.get("stance")
    dim = ((oie.get("dimensions") or {}).get("valuation") or {})
    signals = dim.get("signals") or []
    if stance and signals:
        return f"Stance: {stance}. Signals: {', '.join(signals[:3])}."
    if stance:
        return f"Valuation stance: {stance}."
    if signals:
        return ", ".join(signals[:3])
    return "Valuation context limited in compiled memory."


def _graph_text(graph: dict[str, Any]) -> str:
    if not graph.get("n_nodes"):
        return "Knowledge graph slice unavailable."
    peers = ", ".join((graph.get("peers") or [])[:4]) or "n/a"
    themes = ", ".join((graph.get("themes") or [])[:4]) or "n/a"
    return f"Sector {graph.get('sector_key') or 'n/a'}; peers {peers}; themes {themes}."


def _list_text(items: list[Any], *, empty: str) -> str:
    clean = [str(x) for x in items if x]
    return "; ".join(clean[:6]) if clean else empty


def _actions(rtype: str, oie: dict[str, Any], kd: dict[str, Any]) -> str:
    bits = [f"Review {rtype.replace('_', ' ')} draft against CompanyMemory evidence."]
    if kd.get("status") and kd.get("status") != "UNCHANGED":
        bits.append("Validate Knowledge Delta fields before publication.")
    if oie.get("research_priority") in {"Critical", "High"}:
        bits.append(f"Elevate in research queue ({oie.get('research_priority')}).")
    bits.append("Do not issue BUY/SELL; route through governance if publishing.")
    return " ".join(bits)
