"""Adapt Ask Track B/C outputs into a single InstitutionalAnswer for ICE."""

from __future__ import annotations

from typing import Any


def build_institutional_answer(
    *,
    question: str,
    intent_resolution: dict[str, Any] | None = None,
    answer_assembly: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    playbook_selection: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    institutional_answer: dict[str, Any] | None = None,
    governance: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
    replay_id: str | None = None,
) -> dict[str, Any]:
    """Merge existing objects only — never invent facts or re-reason."""
    irl = intent_resolution or {}
    aa = answer_assembly or {}
    fs = framework_selection or {}
    ia = institutional_answer or {}
    ps = playbook_selection or ia_playbook(ia)
    eg = evidence_graph or ia_evidence_graph(ia)
    im = institutional_memory or ia_institutional_memory(ia)
    gov = governance or {}
    kn = knowledge or {}
    iere = kn.get("iere") if isinstance(kn.get("iere"), dict) else {}
    envelope = iere.get("ask_envelope") if isinstance(iere.get("ask_envelope"), dict) else {}

    sections = ia.get("sections") if isinstance(ia.get("sections"), dict) else {}
    skeleton = (aa.get("skeleton") or {}).get("sections") if isinstance(aa.get("skeleton"), dict) else {}
    # Prefer bound institutional sections; fall back to assembly skeleton bullets
    merged_sections: dict[str, Any] = {}
    order = (
        (aa.get("skeleton") or {}).get("section_order")
        or list(sections.keys())
        or [
            "executive_summary",
            "evidence",
            "analysis",
            "framework",
            "risks",
            "conclusion",
            "confidence",
            "sources",
        ]
    )
    for name in order:
        bound = sections.get(name) if isinstance(sections.get(name), dict) else {}
        planned = skeleton.get(name) if isinstance(skeleton.get(name), dict) else {}
        bullets = list(bound.get("bullets") or planned.get("bullets") or [])
        eids = list(bound.get("evidence_ids") or planned.get("evidence_ids") or [])
        merged_sections[name] = {
            "section": name,
            "bullets": bullets,
            "evidence_ids": eids,
            "citations": bound.get("citations") or [],
        }

    top_evidence = []
    for item in envelope.get("top_evidence") or iere.get("ranked_evidence") or []:
        if isinstance(item, dict):
            top_evidence.append(
                {
                    "evidence_id": item.get("evidence_id"),
                    "evidence_type": item.get("evidence_type"),
                    "title": item.get("title"),
                    "source": item.get("source") or (item.get("citation") or {}).get("source"),
                    "document_id": item.get("document_id")
                    or (item.get("citation") or {}).get("document_id"),
                    "company": item.get("company"),
                    "available_from": item.get("available_from"),
                }
            )

    # Also surface ordered assembly evidence titles
    ordered = ((aa.get("ordering") or {}).get("ordered")) or []
    if not top_evidence and ordered:
        for item in ordered[:15]:
            if isinstance(item, dict):
                top_evidence.append(
                    {
                        "evidence_id": item.get("evidence_id"),
                        "evidence_type": item.get("evidence_type"),
                        "title": item.get("title"),
                        "source": item.get("source"),
                        "document_id": item.get("document_id"),
                        "domain": item.get("domain"),
                        "available_from": item.get("available_from"),
                    }
                )

    gaps = aa.get("gaps") or ia.get("gaps") or {}
    conf = fs.get("confidence") or aa.get("confidence") or ia.get("confidence") or {}
    expl = fs.get("explanation") or (ia.get("framework_selection") or {}).get("explanation") or {}

    return {
        "format": "institutional_answer_v1",
        "question": question,
        "intent_v2": irl.get("intent") or ia.get("intent_v2"),
        "question_type": irl.get("question_type") or gov.get("question_type"),
        "concept_mode": bool(irl.get("concept_mode")),
        "as_of": irl.get("as_of"),
        "replay_id": replay_id or iere.get("retrieval_id"),
        "governance_path": gov.get("path"),
        "sections": merged_sections,
        "section_order": list(order),
        "evidence": {
            "items": top_evidence,
            "pack_names": list(((evidence or {}).get("packs") or {}).keys()),
            "iere_ranked_count": iere.get("ranked_count"),
            "retrieval_id": iere.get("retrieval_id"),
        },
        "frameworks": {
            "selected": fs.get("selected") or [],
            "primary": fs.get("primary") or [],
            "secondary": fs.get("secondary") or [],
            "supporting": fs.get("supporting") or [],
            "framework_ids": fs.get("framework_ids") or [],
            "forbidden_rejected": fs.get("forbidden_rejected") or [],
            "explanation": expl,
            "confidence": fs.get("confidence") or {},
            "sector": fs.get("sector"),
            "ifse_version": fs.get("ifse_version"),
        },
        "playbook": {
            "playbook_id": ps.get("playbook_id"),
            "playbook_name": ps.get("playbook_name") or (ps.get("primary") or {}).get("name"),
            "category": ps.get("category"),
            "checklist": ps.get("checklist") or {},
            "procedure": ps.get("procedure") or {},
            "common_mistakes": ps.get("common_mistakes") or [],
            "output_structure": ps.get("output_structure") or [],
            "explanation": ps.get("explanation") or {},
            "confidence": ps.get("confidence") or {},
            "iap_version": ps.get("iap_version"),
            "guides_reasoning": True,
        },
        "evidence_graph": {
            "graph_id": eg.get("graph_id"),
            "entities": eg.get("entities") or [],
            "n_nodes": eg.get("n_nodes"),
            "n_edges": eg.get("n_edges"),
            "domain_coverage_pct": eg.get("domain_coverage_pct"),
            "chains": eg.get("chains") or [],
            "chain_bullets": eg.get("chain_bullets") or [],
            "surface_bullets": eg.get("surface_bullets") or [],
            "as_of": eg.get("as_of"),
            "ieg_version": eg.get("ieg_version"),
            "guides_evidence": True,
        },
        "institutional_memory": {
            "imai_version": im.get("imai_version") or im.get("version"),
            "have_we_seen_this_before": bool(im.get("have_we_seen_this_before")),
            "top_memory_ids": im.get("top_memory_ids") or [],
            "memories": im.get("memories") or [],
            "surface_bullets": im.get("surface_bullets") or [],
            "comparison": im.get("comparison") or {},
            "regimes": im.get("regimes") or [],
            "as_of": im.get("as_of"),
            "guides_memory": True,
            "invented_analogues": False,
        },
        "gaps": gaps,
        "confidence": conf,
        "citations": aa.get("citations") or {},
        "answer_plan": aa.get("answer_plan") or ia.get("answer_plan") or {},
        "risk_signals": {
            "missing_domains": gaps.get("missing_domains") or [],
            "softened_domains": gaps.get("softened_domains") or [],
            "tell_reasoning": gaps.get("tell_reasoning"),
            "confidence_penalty": gaps.get("confidence_penalty"),
            "disagreements": ((gov.get("committee") or {}).get("disagreements") or [])[:5],
        },
        "replay": {
            "as_of": irl.get("as_of"),
            "replay_flag": bool(iere.get("replay")) or bool(irl.get("as_of")),
            "retrieval_id": iere.get("retrieval_id"),
            "ranked_count": iere.get("ranked_count"),
        },
        "source_objects": {
            "has_answer_assembly": bool(aa),
            "has_framework_selection": bool(fs),
            "has_playbook_selection": bool(ps),
            "has_evidence_graph": bool(eg),
            "has_institutional_memory": bool(im.get("top_memory_ids") or im.get("memories")),
            "has_institutional_answer": bool(ia),
            "has_governance": bool(gov),
        },
        "fabricated": False,
        "llm_used": False,
        "reasoning_changed": False,
    }


def ia_playbook(institutional_answer: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(institutional_answer, dict):
        return {}
    ps = institutional_answer.get("playbook_selection")
    return ps if isinstance(ps, dict) else {}


def ia_evidence_graph(institutional_answer: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(institutional_answer, dict):
        return {}
    eg = institutional_answer.get("evidence_graph")
    return eg if isinstance(eg, dict) else {}


def ia_institutional_memory(institutional_answer: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(institutional_answer, dict):
        return {}
    im = institutional_answer.get("institutional_memory")
    return im if isinstance(im, dict) else {}
