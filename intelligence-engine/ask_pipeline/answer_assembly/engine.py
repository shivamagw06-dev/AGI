"""Institutional Answer Assembly Engine — Evidence → Plan → Skeleton → Reasoning bind."""

from __future__ import annotations

from typing import Any

from ask_pipeline.answer_assembly.citations import map_citations
from ask_pipeline.answer_assembly.classify import classify_evidence
from ask_pipeline.answer_assembly.confidence import calibrate_confidence
from ask_pipeline.answer_assembly.gaps import detect_gaps
from ask_pipeline.answer_assembly.ordering import order_evidence
from ask_pipeline.answer_assembly.schema import AAE_VERSION, FREEZE_LOCKS, MODULE_CODE, PROGRAMME
from ask_pipeline.answer_assembly.skeleton import build_skeleton


def assemble_answer_plan(
    *,
    question: str,
    intent_v2: str,
    evidence: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
    intent_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stages 1–6 before existing reasoning. Deterministic — no LLM."""
    irl = intent_resolution or {}
    evidence = evidence or {}
    knowledge = knowledge or {}

    iere = knowledge.get("iere") if isinstance(knowledge.get("iere"), dict) else {}
    envelope = iere.get("ask_envelope") if isinstance(iere.get("ask_envelope"), dict) else {}
    # Prefer full IERE ranked list → envelope top_evidence → assembled pack slice
    top: list[Any] = []
    if isinstance(iere.get("ranked_evidence"), list) and iere["ranked_evidence"]:
        top = list(iere["ranked_evidence"])
    elif isinstance(envelope.get("top_evidence"), list) and envelope["top_evidence"]:
        top = list(envelope["top_evidence"])
    else:
        iere_pack = ((evidence.get("packs") or {}).get("iere") or {}).get("evidence") or {}
        if isinstance(iere_pack.get("top_evidence"), list):
            top = list(iere_pack["top_evidence"])

    classified = classify_evidence(
        iere_items=top,
        evidence_packs=evidence.get("packs"),
        intent_v2=intent_v2,
    )
    ordered = order_evidence(classified, intent_v2=intent_v2)
    req = (irl.get("evidence_requirements") or {}).get("evidence_types_required") or []
    gaps = detect_gaps(
        classified,
        intent_v2=intent_v2,
        evidence_types_required=req,
    )
    skeleton = build_skeleton(
        question=question,
        intent_v2=intent_v2,
        ordered=ordered,
        gaps=gaps,
        concept_mode=bool(irl.get("concept_mode")),
        as_of=irl.get("as_of"),
    )
    confidence = calibrate_confidence(classified=classified, gaps=gaps, ordered=ordered)
    # Write confidence into skeleton
    skeleton["sections"]["confidence"]["bullets"] = [
        f"Band: {confidence['band']}",
        f"Score: {confidence['score']}",
        f"Coverage: {confidence['coverage']}",
        f"Missing: {', '.join(confidence['missing_domains']) or 'none'}",
    ]
    skeleton["sections"]["confidence"]["status"] = "calibrated"

    citations = map_citations(
        skeleton=skeleton,
        ordered=ordered,
        retrieval_id=iere.get("retrieval_id") or envelope.get("retrieval_id"),
        as_of=irl.get("as_of"),
    )

    utilised = len([i for i in (ordered.get("ordered") or []) if i.get("assembly_rank")])
    utilisation = round(utilised / max(classified.get("item_count") or 1, 1), 4)

    return {
        "ok": True,
        "aae_version": AAE_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "intent_v2": intent_v2,
        "classification": classified,
        "ordering": ordered,
        "gaps": gaps,
        "skeleton": skeleton,
        "confidence": confidence,
        "citations": citations,
        "metrics": {
            "evidence_utilisation": utilisation,
            "item_count": classified.get("item_count"),
            "gap_count": len(gaps.get("missing_domains") or []),
            "citation_coverage": citations.get("coverage"),
            "generic_answer": False,
            "free_form": False,
        },
        "answer_plan": {
            "section_order": skeleton.get("section_order"),
            "top_evidence_ids": ordered.get("top_evidence_ids"),
            "framework_inputs": ordered.get("framework_inputs"),
            "tell_reasoning": gaps.get("tell_reasoning"),
            "confidence_band": confidence.get("band"),
            "concept_mode": bool(irl.get("concept_mode")),
            "as_of": irl.get("as_of"),
        },
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "llm_used": False,
    }


def bind_reasoning_to_answer(
    plan: dict[str, Any],
    *,
    governance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """After existing reasoning — fill skeleton slots without inventing facts."""
    gov = governance or {}
    skeleton = dict(plan.get("skeleton") or {})
    sections = {k: dict(v) for k, v in (skeleton.get("sections") or {}).items()}

    path = gov.get("path")
    committee = gov.get("committee") or {}
    conclusion = committee.get("conclusion") or ""
    findings = committee.get("findings") or []
    disagreements = committee.get("disagreements") or []

    # Executive summary from governance path / stance
    exec_bits = [
        f"Governance path: {path or 'n/a'}",
        f"Question type: {gov.get('question_type')}",
    ]
    if committee.get("stance"):
        exec_bits.append(f"Committee stance: {committee.get('stance')}")
    if path == "education":
        exec_bits.append("Education / explanation path — no valuation conclusion")
    sections["executive_summary"]["bullets"] = (
        list((sections.get("executive_summary") or {}).get("bullets") or [])[:2] + exec_bits
    )
    sections["executive_summary"]["status"] = "filled"

    # Analysis / conclusion from committee findings (structured only)
    analysis_bullets = list((sections.get("analysis") or {}).get("bullets") or [])
    for f in findings[:6]:
        if isinstance(f, dict):
            analysis_bullets.append(
                str(f.get("finding") or f.get("summary") or f.get("framework") or f)[:240]
            )
        else:
            analysis_bullets.append(str(f)[:240])
    sections["analysis"]["bullets"] = analysis_bullets
    sections["analysis"]["status"] = "filled"

    if conclusion:
        sections["conclusion"]["bullets"] = [
            str(conclusion)[:500],
            *list((sections.get("conclusion") or {}).get("bullets") or [])[:2],
        ]
    risk_bullets = list((sections.get("risks") or {}).get("bullets") or [])
    for d in disagreements[:3]:
        risk_bullets.append(f"Disagreement: {str(d)[:200]}")
    sections.setdefault("risks", {"section": "risks", "bullets": [], "evidence_ids": [], "status": "planned"})
    sections["risks"]["bullets"] = risk_bullets
    sections["conclusion"]["status"] = "filled"
    sections["risks"]["status"] = "filled"
    sections["evidence"]["status"] = "filled"
    sections["framework"]["status"] = "filled"
    sections["sources"]["status"] = "filled"

    skeleton["sections"] = sections
    conf = plan.get("confidence") or {}

    institutional_answer = {
        "format": "institutional_skeleton_v1",
        "intent_v2": plan.get("intent_v2"),
        "path": path,
        "confidence": conf,
        "sections": {
            name: {
                "bullets": (sections.get(name) or {}).get("bullets") or [],
                "evidence_ids": (sections.get(name) or {}).get("evidence_ids") or [],
                "citations": ((plan.get("citations") or {}).get("by_section") or {}).get(name) or [],
            }
            for name in (skeleton.get("section_order") or [])
        },
        "gaps": plan.get("gaps"),
        "answer_plan": plan.get("answer_plan"),
        "metrics": plan.get("metrics"),
        "generic": False,
        "fabricated": False,
        "llm_used": False,
    }

    return {
        **plan,
        "skeleton": skeleton,
        "governance_bound": True,
        "governance_path": path,
        "institutional_answer": institutional_answer,
        "fabricated": False,
    }
