"""Deterministic Research Intelligence engines — Phase 3.4.

Transform structured research memory into institutional research outputs.
Not document summarization. No BUY/SELL. No forecasting.
"""

from __future__ import annotations

from typing import Any

from investment_intelligence.policy import strip_recommendation_language
from research_intelligence.schema import KNOWLEDGE_AUTHORITY, RECOMMENDATION_POLICY


def research_object(c: dict[str, Any]) -> dict[str, Any]:
    obj = {
        "research": c["name"],
        "company": c["name"],
        "industry": c["industry"],
        "financial": {"estimate_metrics": (c.get("estimates") or {}).get("metrics"), "kpis_from_ars": [
            kpi for ar in c.get("annual_reports") or [] for kpi in (ar.get("kpis") or [])
        ][:12]},
        "investment": {"conclusions": (c.get("memory") or {}).get("conclusions"), "themes": (c.get("memory") or {}).get("recurring_themes")},
        "portfolio": {"event_links": [e.get("links", {}).get("portfolio") for e in (c.get("events") or [])[:6]]},
        "macro": ["rates" if c["industry"] == "banks" else "fx" if c["industry"] == "it_services" else "commodity_inputs"],
        "evidence": {"document_count": len(c.get("documents") or []), "transcript_count": len(c.get("transcripts") or [])},
        "sources": c.get("documents") or [],
        "conclusions": (c.get("memory") or {}).get("conclusions") or [],
        "unknowns": c.get("unknowns") or [],
        "monitoring": c.get("monitoring") or [],
        "knowledge_authority": KNOWLEDGE_AUTHORITY,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }
    summary = strip_recommendation_language(
        f"Canonical research object for {c['name']}: links company, industry, financial KPIs, "
        f"investment conclusions, portfolio event links, macro drivers, evidence/sources, "
        f"conclusions, unknowns, and monitoring. "
        f"Research Intelligence is the sole long-lived research memory authority — "
        f"other layers consume these objects. Observations only — no BUY/SELL."
    )
    return {"research_object": obj, "summary": summary, "fabricated": False}


def annual_report_intelligence(c: dict[str, Any]) -> dict[str, Any]:
    reports = c.get("annual_reports") or []
    latest = reports[-1] if reports else {}
    extract_keys = [
        "business", "strategy", "products", "segments", "customers", "management",
        "capital_allocation", "risks", "kpis", "guidance", "governance", "financial_changes",
    ]
    extracted = {k: latest.get(k) for k in extract_keys}
    themes = []
    for ar in reports:
        themes.extend(ar.get("themes") or [])
    summary = strip_recommendation_language(
        f"Annual report intelligence for {c['name']} (latest {latest.get('fy', 'n/a')}): "
        f"business — {extracted.get('business')}; strategy — {extracted.get('strategy')}; "
        f"segments — {extracted.get('segments')}; capital allocation — {extracted.get('capital_allocation')}; "
        f"risks — {extracted.get('risks')}; KPIs — {extracted.get('kpis')}; "
        f"guidance — {extracted.get('guidance')}; governance — {extracted.get('governance')}; "
        f"financial changes — {extracted.get('financial_changes')}. "
        f"Recurring themes across reports: {', '.join(sorted(set(themes))[:8])}. "
        f"Stored as structured research memory — not a summary dump. No BUY/SELL."
    )
    return {
        "latest_fy": latest.get("fy"),
        "extracted": extracted,
        "reports": [{"fy": r.get("fy"), "themes": r.get("themes"), "strategy": r.get("strategy")} for r in reports],
        "themes": sorted(set(themes)),
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def transcript_intelligence(c: dict[str, Any]) -> dict[str, Any]:
    txs = c.get("transcripts") or []
    latest = txs[-1] if txs else {}
    fields = [
        "management_commentary", "analyst_questions", "management_confidence", "guidance_changes",
        "demand_commentary", "margin_commentary", "pricing", "capex", "hiring", "customer_commentary",
    ]
    structured = {k: latest.get(k) for k in fields}
    pricing_track = [t.get("pricing") for t in txs]
    summary = strip_recommendation_language(
        f"Earnings transcript intelligence for {c['name']} ({latest.get('period', 'n/a')}): "
        f"management commentary — {structured.get('management_commentary')}; "
        f"analyst questions — {structured.get('analyst_questions')}; "
        f"management confidence — {structured.get('management_confidence')}; "
        f"guidance changes — {structured.get('guidance_changes')}; "
        f"demand — {structured.get('demand_commentary')}; margins — {structured.get('margin_commentary')}; "
        f"pricing — {structured.get('pricing')}; capex — {structured.get('capex')}; "
        f"hiring — {structured.get('hiring')}; customers — {structured.get('customer_commentary')}. "
        f"Pricing commentary tracked across calls: {pricing_track}. "
        f"Each transcript is structured intelligence, not a paraphrase. No BUY/SELL."
    )
    return {
        "latest_period": latest.get("period"),
        "structured": structured,
        "transcripts": [{"period": t.get("period"), "management_confidence": t.get("management_confidence")} for t in txs],
        "pricing_commentary_track": pricing_track,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def management_intelligence(c: dict[str, Any]) -> dict[str, Any]:
    m = c.get("management") or {}
    summary = strip_recommendation_language(
        f"Management intelligence for {c['name']}: CEO — {m.get('ceo')}; CFO — {m.get('cfo')}; "
        f"Chairman — {m.get('chairman')}. Capital allocation — {m.get('capital_allocation')}. "
        f"Communication — {m.get('communication')}. Consistency — {m.get('consistency')}. "
        f"Execution — {m.get('execution')}. Historical accuracy — {m.get('historical_accuracy')}. "
        f"Philosophy — {m.get('philosophy')}. Leadership changes — {m.get('leadership_changes')}. "
        f"Track what management has consistently emphasized over time. Observations only."
    )
    return {
        "management": m,
        "consistently_emphasized": (c.get("deep_research") or {}).get("management_emphasis"),
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def guidance_intelligence(c: dict[str, Any]) -> dict[str, Any]:
    hist = c.get("guidance_history") or []
    latest = hist[-1] if hist else {}
    summary = strip_recommendation_language(
        f"Guidance intelligence for {c['name']} ({latest.get('period', 'n/a')}): "
        f"revenue — {latest.get('revenue_guidance')}; margin — {latest.get('margin_guidance')}; "
        f"capex — {latest.get('capex_guidance')}; hiring — {latest.get('hiring_guidance')}; "
        f"demand — {latest.get('demand_commentary')}; pricing — {latest.get('pricing_commentary')}. "
        f"Vs previous — {latest.get('vs_previous')}. Vs consensus — {latest.get('vs_consensus')}. "
        f"Vs actual — {latest.get('vs_actual')}. "
        f"Guidance evolution is tracked structurally across periods. No forecasting. No BUY/SELL."
    )
    return {
        "latest": latest,
        "history": hist,
        "evolution": (c.get("deep_research") or {}).get("guidance_accuracy"),
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def estimate_intelligence(c: dict[str, Any]) -> dict[str, Any]:
    e = c.get("estimates") or {}
    summary = strip_recommendation_language(
        f"Estimate intelligence for {c['name']}: tracks {', '.join(e.get('metrics') or [])}. "
        f"Consensus focus — {e.get('consensus_focus')}. Revisions — {e.get('revisions')}. "
        f"Expectation gaps — {e.get('expectation_gaps')}. "
        f"{e.get('note')}. Structured comparison only — no forecasting, no BUY/SELL."
    )
    return {
        "estimates": e,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def event_intelligence(c: dict[str, Any]) -> dict[str, Any]:
    events = c.get("events") or []
    by_type: dict[str, list] = {}
    for ev in events:
        by_type.setdefault(str(ev.get("type")), []).append(ev)
    summary = strip_recommendation_language(
        f"Event intelligence for {c['name']}: {len(events)} structured events covering "
        f"{', '.join(sorted(by_type.keys()))}. "
        f"Each event links to business, industry, investment, and portfolio implications. "
        f"Examples: " + "; ".join(f"{e.get('date')} {e.get('type')} — {e.get('title')}" for e in events[:4])
        + ". Acquisition history and capital actions are first-class research objects. No BUY/SELL."
    )
    return {
        "events": events,
        "by_type": {k: len(v) for k, v in by_type.items()},
        "acquisition_history": (c.get("deep_research") or {}).get("acquisition_history"),
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def research_memory(c: dict[str, Any]) -> dict[str, Any]:
    mem = c.get("memory") or {}
    summary = strip_recommendation_language(
        f"Research memory for {c['name']}: conclusions — {mem.get('conclusions')}. "
        f"Recurring themes — {mem.get('recurring_themes')}. "
        f"Company history — {mem.get('company_history')}. "
        f"Management history — {mem.get('management_history')}. "
        f"Guidance history — {mem.get('guidance_history_note')}. "
        f"Industry evolution — {mem.get('industry_evolution')}. "
        f"{mem.get('dedupe_policy')}. Questions tomorrow improve because memory persists. No BUY/SELL."
    )
    return {
        "memory": mem,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def cross_document(c: dict[str, Any]) -> dict[str, Any]:
    docs = c.get("documents") or []
    types = sorted({d.get("type") for d in docs})
    summary = strip_recommendation_language(
        f"Cross-document intelligence for {c['name']}: one timeline connecting "
        f"{', '.join(types)}. Document set includes annual reports, quarterly/earnings transcripts, "
        f"investor presentations, conference calls, press releases, filings, news, and research notes. "
        f"Count={len(docs)}. Document linkage joins earnings and annual reports into one graph. "
        f"Synthesis is deterministic across the document graph — not isolated summarization."
    )
    return {
        "documents": docs,
        "document_types": types,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def timeline_engine(c: dict[str, Any]) -> dict[str, Any]:
    tl = c.get("timeline") or []
    summary = strip_recommendation_language(
        f"Research timeline for {c['name']}: chronological intelligence covering "
        + "; ".join(f"{t.get('year')} — {t.get('event')} ({t.get('category')})" for t in tl)
        + ". Includes IPO/history, major acquisitions, capital allocation, guidance, leadership, "
        f"industry events, macro-relevant regulatory overlays, major risks, and important decisions."
    )
    return {
        "timeline": tl,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def quality_engine(c: dict[str, Any]) -> dict[str, Any]:
    doc_n = len(c.get("documents") or [])
    tx_n = len(c.get("transcripts") or [])
    ar_n = len(c.get("annual_reports") or [])
    unk_n = len(c.get("unknowns") or [])
    coverage = min(100, 40 + doc_n * 5 + tx_n * 4 + ar_n * 6)
    freshness = "structured_fixture_current" if tx_n and ar_n else "partial"
    contradictions = []
    # Soft contradiction flags from guidance vs themes
    if c["industry"] == "it_services":
        contradictions.append("Growth ambition in boom-year ARs vs cautious transcript demand tone — track as tension, not error")
    if c["key"] == "hdfc_bank":
        contradictions.append("Pre-merger organic narrative vs post-merger funding/NIM distortion — reconcile on timeline")
    dims = {
        "evidence_quality": min(95, 60 + doc_n * 3),
        "freshness": freshness,
        "coverage": coverage,
        "contradictions": contradictions,
        "missing_information": list(c.get("unknowns") or [])[:5],
        "confidence": round(0.55 + min(0.35, doc_n * 0.03), 2),
        "unknowns_count": unk_n,
        "research_completeness": "high" if coverage >= 80 else "medium" if coverage >= 60 else "developing",
    }
    summary = strip_recommendation_language(
        f"Research quality for {c['name']}: evidence quality {dims['evidence_quality']}/100; "
        f"freshness {freshness}; coverage {coverage}/100; completeness {dims['research_completeness']}; "
        f"confidence {dims['confidence']}. Contradictions flagged: {contradictions or ['none hard-flagged']}. "
        f"Missing information: {dims['missing_information']}. Unknowns tracked explicitly. No BUY/SELL."
    )
    return {
        "dimensions": dims,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def knowledge_evolution(c: dict[str, Any]) -> dict[str, Any]:
    path = {
        "research_updates": "Research Memory objects (this layer)",
        "knowledge_updates": "Business Intelligence consumes structured research outputs",
        "business_updates": "Investment Intelligence consumes BI + research conclusions",
        "investment_updates": "Portfolio Intelligence consumes investment objects",
        "authority": KNOWLEDGE_AUTHORITY,
        "rule": "Only Research Intelligence creates new long-lived research knowledge; others consume",
    }
    summary = strip_recommendation_language(
        f"Knowledge evolution for {c['name']}: research updates knowledge; knowledge updates "
        f"Business Intelligence; business updates Investment Intelligence; investment updates "
        f"Portfolio Intelligence. Learning is continuous. "
        f"Authority rule — {path['rule']}. No parallel research memories. No BUY/SELL."
    )
    return {
        "path": path,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def deep_research(c: dict[str, Any]) -> dict[str, Any]:
    d = c.get("deep_research") or {}
    summary = strip_recommendation_language(
        f"Deep research synthesis for {c['name']} (institutional, not document summarization): "
        f"five-year / 5y capital allocation — {d.get('capital_allocation_5y')}. "
        f"10-year / 10y capital allocation — {d.get('capital_allocation_10y')}. "
        f"Management evolution — {d.get('management_evolution')}. "
        f"Industry evolution — {d.get('industry_evolution')}. "
        f"Competitive evolution — {d.get('competitive_evolution')}. "
        f"Risk evolution — {d.get('risk_evolution')}. "
        f"Guidance accuracy — {d.get('guidance_accuracy')}. "
        f"Strategic consistency — {d.get('strategic_consistency')}. "
        f"FY2022 vs FY2026 strategy — {d.get('fy2022_vs_fy2026_strategy')}. "
        f"Pricing commentary across earnings — {d.get('pricing_commentary_track')}. "
        f"Business model change — {d.get('business_model_change')}. "
        f"Management consistently emphasized — {d.get('management_emphasis')}. "
        f"Acquisition history — {d.get('acquisition_history')}. "
        f"Recurring annual report themes — {d.get('annual_report_themes')}. "
        f"Observations only — no BUY/SELL."
    )
    return {
        "deep_research": d,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def executive_brief_bits(c: dict[str, Any], *, whats_new: list[str] | None = None) -> dict[str, Any]:
    mem = c.get("memory") or {}
    latest_tx = (c.get("transcripts") or [{}])[-1]
    latest_ar = (c.get("annual_reports") or [{}])[-1]
    wn = whats_new or [
        f"Latest transcript period {latest_tx.get('period')}: {latest_tx.get('guidance_changes')}",
        f"Latest AR {latest_ar.get('fy')}: strategy — {latest_ar.get('strategy')}",
        f"Open unknowns: {', '.join((c.get('unknowns') or [])[:2])}",
    ]
    return {
        "whats_new": wn,
        "business_impact": strip_recommendation_language(
            f"Business impact for {c['name']}: {latest_ar.get('business')}. "
            f"Model/strategy evolution — {(c.get('deep_research') or {}).get('business_model_change')}."
        ),
        "financial_impact": strip_recommendation_language(
            f"Financial impact lenses: KPIs {latest_ar.get('kpis')}; "
            f"estimate focus {(c.get('estimates') or {}).get('consensus_focus')}; "
            f"guidance vs prior/consensus/actual is tracked structurally."
        ),
        "industry_impact": strip_recommendation_language(
            f"Industry impact: {mem.get('industry_evolution')}. "
            f"Competitive evolution — {(c.get('deep_research') or {}).get('competitive_evolution')}."
        ),
        "investment_implications": strip_recommendation_language(
            f"Investment implications (observational): research conclusions — {mem.get('conclusions')}. "
            f"Not a BUY/SELL recommendation; implications describe what evidence changes for analysis."
        ),
    }
