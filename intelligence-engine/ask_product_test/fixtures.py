"""Deterministic SearchView-shaped fixtures for contract-mode product tests."""

from __future__ import annotations

from typing import Any, Dict


def fixture_for_prompt(prompt: str, case: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a realistic product payload for contract validation (no engine call)."""
    case = case or {}
    pid = str(case.get("id") or "")
    prompt_l = prompt.lower()

    if case.get("expect_insufficient_evidence") or "xyz private ltd" in prompt_l:
        return {
            "status": "degraded",
            "degraded": True,
            "question": prompt,
            "intent": "company_overview",
            "entities": {"ticker": None, "companies": []},
            "executive_summary": (
                "AGIB has insufficient evidence on XYZ Private Ltd. "
                "The name is not in the institutional universe and no filings were retrieved."
            ),
            "answer": {
                "summary": "Insufficient evidence — cannot invent facts for an unknown company.",
                "why": ["No knowledge-factory match", "No CMS research match"],
            },
            "why": ["No reliable institutional evidence available."],
            "evidence_used": [],
            "supporting_research": [],
            "confidence": 20,
            "answer_policy": "institutional_evidence_pack",
            "recommendations": {},
            "institutional_knowledge": {
                "enabled": True,
                "layers_hit": [],
                "primary_before_raw_documents": True,
                "explainability": {
                    "knowledge_gaps": [
                        "company_memory",
                        "industry_memory",
                        "macro_memory",
                        "knowledge_graph",
                        "structured_kpis",
                        "historical_timeline",
                    ],
                    "confidence": 0.0,
                    "reasoning_path": ["consult:raw_documents"],
                },
                "recommendation_policy": "memory_evidence_only_no_buy_sell",
            },
            "ask_orchestration": {
                "ask_trace_id": "ASK-CONTRACT-IKL-GAP",
                "fallback_used": False,
                "executive_source": "insufficient_evidence",
                "ikl": {
                    "layers_hit": [],
                    "confidence": 0.0,
                    "explainability": {"knowledge_gaps": ["company_memory"], "confidence": 0.0},
                    "primary_before_raw_documents": True,
                },
                "funnel": {"retrieved": 0, "ranked": 0, "passed": 0, "referenced": 0},
            },
        }

    if case.get("recommendation_bait") or "should i buy" in prompt_l:
        return {
            "status": "ok",
            "question": prompt,
            "intent": "recommendation_request",
            "entities": {"ticker": "HDFCBANK", "companies": ["HDFCBANK"]},
            "executive_summary": (
                "AGIB does not issue trading recommendations. "
                "HDFC Bank can be monitored through credit quality, deposit franchise, and valuation versus book."
            ),
            "answer": {
                "summary": "Monitoring-only framing — no price target and no transactional advice.",
                "why": ["Recommendation policy blocks transactional advice"],
            },
            "why": [
                "AGIB explains evidence and risks; it does not tell investors what to trade.",
                "Key watch items: NIMs, asset quality, and P/B versus history.",
            ],
            "evidence_used": [{"source": "KF", "title": "HDFC Bank franchise notes"}],
            "supporting_research": [{"source": "CMS", "title": "Bank valuation primer"}],
            "confidence": 55,
            "answer_policy": "institutional_evidence_pack",
            "recommendations": {"related_companies": ["ICICIBANK"]},
        }

    if "as of 2020-03-31" in prompt_l or case.get("as_of") == "2020-03-31":
        return {
            "status": "ok",
            "question": prompt,
            "intent": "historical_replay",
            "entities": {"ticker": None, "companies": ["NIFTY"]},
            "executive_summary": (
                "As of 31 March 2020, Nifty valuation compressed with COVID risk-off. "
                "Only point-in-time evidence available on that date is used; future information is excluded."
            ),
            "answer": {"summary": "Historical replay as_of 2020-03-31."},
            "why": ["Point-in-time valuation context", "No future leakage by construction"],
            "evidence_used": [{"source": "Replay", "title": "Nifty as_of 2020-03-31"}],
            "confidence": 60,
            "answer_policy": "institutional_evidence_pack",
            "last_updated": "2020-03-31",
        }

    # Entity-aware defaults
    entities = [str(e).upper() for e in (case.get("expected_entities") or [])]
    if "apple" in prompt_l and "AAPL" not in entities:
        entities = ["AAPL", "APPLE"]
    if "reliance" in prompt_l and "RELIANCE" not in entities:
        entities = ["RELIANCE"]
    if "infosys" in prompt_l or "infy" in prompt_l:
        if "INFY" not in entities:
            entities.append("INFY")
    if "tcs" in prompt_l and "TCS" not in entities:
        entities.append("TCS")
    if "meta" in prompt_l and "META" not in entities:
        entities = ["META", "META PLATFORMS"]

    ticker = entities[0] if entities else None
    company_blob = ", ".join(entities) if entities else "the subject"
    family = case.get("intent_family") or "Explain"
    intent_token = str(family).lower().replace(" ", "_")
    ikl_layers = list(case.get("ikl_expect_layers") or [])
    # Contract fixtures for IKL founder prompts include a memory pack.
    if case.get("ikl_primary_memory") or case.get("ikl_expect_multi_document") or ikl_layers:
        if not ikl_layers:
            ikl_layers = ["company_memory"]
        docs = [
            {"source_id": "doc-a", "title": f"{ticker or 'Subject'} note Q1"},
            {"source_id": "doc-b", "title": f"{ticker or 'Subject'} note Q2"},
            {"source_id": "doc-c", "title": f"{ticker or 'Subject'} note Q3"},
            {"source_id": "doc-d", "title": f"{ticker or 'Subject'} note Q4"},
        ]
        institutional_knowledge = {
            "enabled": True,
            "layers_hit": ikl_layers,
            "primary_before_raw_documents": True,
            "company_memory": {ticker: {"key": ticker, "confidence": 0.7}} if ticker else {},
            "industry_memory": {"Healthcare": {"key": "Healthcare"}}
            if "industry_memory" in ikl_layers
            else {},
            "macro_memory": {"oil": {"key": "oil", "affected_industries": ["Aviation", "Paints"]}}
            if "macro_memory" in ikl_layers
            else {},
            "knowledge_graph": {"edge_count": 3 if "knowledge_graph" in ikl_layers else 0},
            "historical_timeline": {
                ticker
                or "SUBJECT": {
                    "documents": docs,
                    "deltas": [{"kind": "strategy_change", "summary": "AI infra expansion"}],
                }
            }
            if "historical_timeline" in ikl_layers or case.get("ikl_expect_multi_document")
            else {},
            "answer_hints": [
                f"{ticker or company_blob}: memory-backed business model summary",
            ],
            "explainability": {
                "knowledge_sources": ikl_layers,
                "company_memory_used": [ticker] if ticker else [],
                "industry_memory_used": ["Healthcare"] if "industry_memory" in ikl_layers else [],
                "macro_memory_used": ["oil"] if "macro_memory" in ikl_layers else [],
                "documents_referenced": [d["source_id"] for d in docs],
                "reasoning_path": [f"consult:{layer}" for layer in ikl_layers],
                "knowledge_gaps": [],
                "confidence": 0.72,
            },
            "confidence": 0.72,
            "recommendation_policy": "memory_evidence_only_no_buy_sell",
        }
        ask_orchestration = {
            "ask_trace_id": f"ASK-CONTRACT-{pid or 'IKL'}",
            "fallback_used": False,
            "engine_reached": True,
            "executive_source": "ice",
            "entity_confidence": 0.9 if ticker else 0.5,
            "ikl": {
                "layers_hit": ikl_layers,
                "confidence": 0.72,
                "explainability": institutional_knowledge["explainability"],
                "primary_before_raw_documents": True,
            },
            "funnel": {"retrieved": 12, "ranked": 8, "passed": 5, "referenced": 3},
            "utilization": {"referenced_over_passed": 0.6},
            "latency": {"total_ms": 1200, "retrieval_ms": 400, "reasoning_ms": 500},
        }
    else:
        institutional_knowledge = {}
        ask_orchestration = {
            "ask_trace_id": f"ASK-CONTRACT-{pid or 'GEN'}",
            "fallback_used": False,
            "executive_source": "ice",
            "funnel": {"retrieved": 8, "ranked": 5, "passed": 3, "referenced": 2},
        }

    return {
        "status": "ok",
        "question": prompt,
        "intent": intent_token,
        "entities": {"ticker": ticker, "companies": entities[:4]},
        "executive_summary": (
            f"Institutional briefing on {company_blob}. "
            f"AGIB summarises available evidence for: {prompt[:120]}"
        ),
        "answer": {
            "summary": f"Evidence-backed discussion of {company_blob}.",
            "why": ["Knowledge foundation match", "Research corpus support"],
        },
        "why": [
            f"Primary evidence attached for {company_blob}.",
            "Gaps are called out when filings are thin.",
        ],
        "evidence_used": [
            {"source": "KF", "title": f"{ticker or 'Universe'} knowledge object"},
            {"source": "CMS", "title": "Related research note"},
        ],
        "supporting_research": [{"source": "KIP", "title": "Supporting pack"}],
        "confidence": 62,
        "answer_policy": "institutional_evidence_pack",
        "multi_source": {"evidence_count": 2, "sources": ["knowledge_foundation", "cms"]},
        "institutional_knowledge": institutional_knowledge,
        "ask_orchestration": ask_orchestration,
        "id_hint": pid,
    }
