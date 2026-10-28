"""Ask consult — retrieval order: memory → graph → KPIs → timeline → (caller: raw/live).

Never issues recommendations. Soft — never raises.
"""

from __future__ import annotations

import re
from typing import Any

from institutional_knowledge_layer.deltas import timeline_for
from institutional_knowledge_layer.flags import ikl_ask_consult_enabled
from institutional_knowledge_layer.graph import package_for_ask as graph_package
from institutional_knowledge_layer.memory.company import read_company_memory
from institutional_knowledge_layer.memory.industry import read_industry_memory
from institutional_knowledge_layer.memory.macro import detect_macro_topics, read_macro_memory
from institutional_knowledge_layer.schema import ASK_RETRIEVAL_ORDER, IKL_CODE, IKL_VERSION, now_ts


_TIMELINE_QUERY_RE = re.compile(
    r"\b(history|historical|timeline|what changed|since|previous|prior|"
    r"quarter|quarterly|earnings|results|annual report|filing|guidance)\b",
    re.I,
)


def _slot_preview(slots: dict[str, Any], keys: list[str], *, n: int = 4) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for k in keys:
        vals = slots.get(k)
        if isinstance(vals, list) and vals:
            out[k] = vals[:n]
        elif isinstance(vals, dict) and vals:
            out[k] = [vals]
    return out


def consult(
    *,
    question: str,
    ticker: str | None = None,
    companies: list[str] | None = None,
    industries: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble institutional memory pack for Ask (before raw documents)."""
    if not ikl_ask_consult_enabled():
        return {
            "enabled": False,
            "engine": IKL_CODE,
            "skipped": True,
            "retrieval_order": list(ASK_RETRIEVAL_ORDER),
        }
    try:
        q = (question or "").strip()
        company_ids: list[str] = []
        if ticker:
            company_ids.append(str(ticker).upper())
        for c in companies or []:
            cu = str(c).upper()
            if cu and cu not in company_ids:
                company_ids.append(cu)

        company_memories: dict[str, Any] = {}
        for cid in company_ids[:5]:
            mem = read_company_memory(cid)
            if mem:
                slots = mem.get("slots") or {}
                company_memories[cid] = {
                    "key": cid,
                    "update_count": mem.get("update_count"),
                    "confidence": (slots.get("evidence_confidence") or mem.get("evidence_confidence")),
                    "preview": _slot_preview(
                        slots,
                        [
                            "identity",
                            "business_model",
                            "revenue_segments",
                            "products_services",
                            "key_risks",
                            "investment_highlights",
                            "latest_guidance",
                            "historical_kpis",
                            "competitive_position",
                            "industry_relationships",
                        ],
                    ),
                    "document_timeline_n": len(slots.get("document_timeline") or []),
                    "last_updated": slots.get("last_updated") or mem.get("updated_at"),
                }

        # Industries from explicit list + company memory links
        ind_keys: list[str] = [str(i) for i in (industries or []) if i]
        for cm in company_memories.values():
            for ind in (cm.get("preview") or {}).get("industry_relationships") or []:
                if ind and str(ind) not in ind_keys:
                    ind_keys.append(str(ind))
        industry_memories: dict[str, Any] = {}
        for ind in ind_keys[:6]:
            mem = read_industry_memory(ind)
            if mem:
                slots = mem.get("slots") or {}
                industry_memories[ind] = {
                    "key": ind,
                    "update_count": mem.get("update_count"),
                    "confidence": slots.get("evidence_confidence"),
                    "preview": _slot_preview(
                        slots,
                        [
                            "growth_drivers",
                            "competitive_dynamics",
                            "regulation",
                            "current_trends",
                            "typical_kpis",
                            "representative_companies",
                            "macro_sensitivity",
                        ],
                    ),
                    "last_updated": slots.get("last_updated") or mem.get("updated_at"),
                }

        macro_topics = detect_macro_topics(q)
        # also pull macro exposure from company memory
        for cm in company_memories.values():
            for m in (cm.get("preview") or {}).get("macro_exposure") or []:
                # commodities etc. — map loosely
                t = str(m).strip().lower().replace(" ", "_")
                if t and t not in macro_topics:
                    macro_topics.append(t)
        macro_memories: dict[str, Any] = {}
        for topic in macro_topics[:8]:
            mem = read_macro_memory(topic)
            if mem:
                macro_memories[topic] = {
                    "key": topic,
                    "update_count": mem.get("update_count"),
                    "confidence": mem.get("evidence_confidence"),
                    "events": (mem.get("events") or [])[-6:],
                    "affected_industries": (mem.get("affected_industries") or [])[:8],
                    "last_updated": mem.get("last_updated") or mem.get("updated_at"),
                }

        kg = graph_package(company_ids=company_ids, industries=ind_keys)

        structured_kpis: dict[str, Any] = {}
        for cid, cm in company_memories.items():
            kpis = (cm.get("preview") or {}).get("historical_kpis") or []
            if kpis:
                structured_kpis[cid] = kpis[:8]

        # Timeline reads are the most expensive part of a memory consult.  A
        # current-state comparison already has company memory and structured KPIs;
        # only load dated history when the user actually asks a historical question.
        timelines: dict[str, Any] = {}
        timeline_requested = bool(_TIMELINE_QUERY_RE.search(q))
        if timeline_requested:
            for cid in company_ids[:5]:
                deltas = timeline_for(cid, limit=20)
                mem = read_company_memory(cid)
                docs = ((mem or {}).get("slots") or {}).get("document_timeline") or []
                timelines[cid] = {
                    "deltas": deltas,
                    "documents": docs[-12:],
                }

        layers_hit = []
        if company_memories:
            layers_hit.append("company_memory")
        if industry_memories:
            layers_hit.append("industry_memory")
        if macro_memories:
            layers_hit.append("macro_memory")
        if kg.get("edge_count"):
            layers_hit.append("knowledge_graph")
        if structured_kpis:
            layers_hit.append("structured_kpis")
        if any((timelines.get(c) or {}).get("deltas") or (timelines.get(c) or {}).get("documents") for c in timelines):
            layers_hit.append("historical_timeline")

        gaps = [layer for layer in ASK_RETRIEVAL_ORDER[:6] if layer not in layers_hit]

        confs = []
        for cm in company_memories.values():
            if cm.get("confidence") is not None:
                confs.append(float(cm["confidence"]))
        for im in industry_memories.values():
            if im.get("confidence") is not None:
                confs.append(float(im["confidence"]))
        overall = round(sum(confs) / len(confs), 3) if confs else 0.0

        # Compact reasoning path for internal explainability (never end-user)
        reasoning_path = [
            f"consult:{layer}" for layer in ASK_RETRIEVAL_ORDER if layer in layers_hit or layer in ("raw_documents", "live_search")
        ]

        answer_hints: list[str] = []
        for cid, cm in company_memories.items():
            prev = cm.get("preview") or {}
            if prev.get("latest_guidance"):
                answer_hints.append(f"{cid} guidance: {prev['latest_guidance'][0]}")
            if prev.get("key_risks"):
                answer_hints.append(f"{cid} risk: {prev['key_risks'][0]}")
            if prev.get("investment_highlights"):
                answer_hints.append(f"{cid} highlight: {prev['investment_highlights'][0]}")
        for ind, im in industry_memories.items():
            prev = im.get("preview") or {}
            if prev.get("current_trends"):
                answer_hints.append(f"{ind} trend: {prev['current_trends'][0]}")

        return {
            "enabled": True,
            "engine": IKL_CODE,
            "version": IKL_VERSION,
            "retrieval_order": list(ASK_RETRIEVAL_ORDER),
            "layers_hit": layers_hit,
            "company_memory": company_memories,
            "industry_memory": industry_memories,
            "macro_memory": macro_memories,
            "knowledge_graph": kg,
            "structured_kpis": structured_kpis,
            "historical_timeline": timelines,
            "timeline_requested": timeline_requested,
            "answer_hints": answer_hints[:12],
            "explainability": {
                "knowledge_sources": layers_hit,
                "company_memory_used": list(company_memories.keys()),
                "industry_memory_used": list(industry_memories.keys()),
                "macro_memory_used": list(macro_memories.keys()),
                "documents_referenced": [
                    d.get("source_id")
                    for t in timelines.values()
                    for d in (t.get("documents") or [])
                    if d.get("source_id")
                ][:20],
                "evidence_referenced": answer_hints[:8],
                "reasoning_path": reasoning_path,
                "knowledge_gaps": gaps,
                "confidence": overall,
            },
            "confidence": overall,
            "primary_before_raw_documents": True,
            "recommendation_policy": "memory_evidence_only_no_buy_sell",
            "consulted_at": now_ts(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "engine": IKL_CODE,
            "ok": False,
            "error": str(exc)[:200],
            "soft": True,
            "retrieval_order": list(ASK_RETRIEVAL_ORDER),
        }


def package_for_ask_agi(
    question: str,
    *,
    ticker: str | None = None,
    companies: list[str] | None = None,
    industries: list[str] | None = None,
) -> dict[str, Any]:
    return consult(
        question=question,
        ticker=ticker,
        companies=companies,
        industries=industries,
    )
