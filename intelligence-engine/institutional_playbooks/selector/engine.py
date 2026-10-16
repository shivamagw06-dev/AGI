"""IAP selector — deterministic playbook + checklist composition."""

from __future__ import annotations

import re
from typing import Any

from institutional_playbooks.checklist.expand import expand_checklist, guided_procedure
from institutional_playbooks.confidence.rules import score_playbook_confidence
from institutional_playbooks.quality.gates import validate_selection
from institutional_playbooks.registry.index import get_playbook, list_playbooks
from institutional_playbooks.replay.filter import filter_by_as_of
from institutional_playbooks.schema import FREEZE_LOCKS, IAP_VERSION, MODULE_CODE, PROGRAMME


def _cue_match(cue: str, question_low: str) -> bool:
    """Match multi-word cues as substrings; single tokens as word boundaries.

    Prevents false hits like cue 'repo' matching inside 'report'.
    """
    cue = (cue or "").strip().lower()
    if not cue:
        return False
    if " " in cue or "/" in cue or "-" in cue:
        return cue in question_low
    return re.search(rf"(?<![a-z0-9]){re.escape(cue)}(?![a-z0-9])", question_low) is not None


def select_playbook(
    *,
    question: str,
    intent_v2: str | None = None,
    question_type: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    sector: str | None = None,
    framework_ids: list[str] | None = None,
    framework_selection: dict[str, Any] | None = None,
    concept_mode: bool = False,
    as_of: str | None = None,
    answer_assembly: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select institutional playbook after Framework Selection, before Reasoning."""
    fs = framework_selection or {}
    sector = sector or fs.get("sector") or "generic"
    framework_ids = list(framework_ids or fs.get("framework_ids") or [])
    qtype = (question_type or "").strip()
    low = (question or "").lower()
    fw_set = {str(x) for x in framework_ids}

    scored: list[tuple[int, dict[str, Any], list[str]]] = []
    for pb in list_playbooks():
        score, reasons = _score_playbook(
            pb,
            question_low=low,
            question_type=qtype,
            intent_v2=intent_v2 or "",
            sector=str(sector),
            fw_set=fw_set,
            concept_mode=concept_mode,
        )
        if score > 0:
            scored.append((score, pb, reasons))

    scored.sort(
        key=lambda t: (-t[0], -int(t[1].get("priority") or 0), str(t[1].get("playbook_id")))
    )

    primary = scored[0][1] if scored else _fallback_playbook(sector=str(sector), fw_set=fw_set)
    primary_reasons = scored[0][2] if scored else ["fallback:generic_company_quality"]
    supporting = [t[1] for t in scored[1:4] if t[1]["playbook_id"] != primary["playbook_id"]]

    # Replay filter (soft — currently all V1 playbooks available)
    selected_rows = [primary] + supporting
    selected_rows, dropped = filter_by_as_of(selected_rows, as_of=as_of)

    if not selected_rows:
        primary = _fallback_playbook(sector=str(sector), fw_set=fw_set)
        selected_rows = [primary]
        primary_reasons = ["fallback:after_replay_filter"]

    primary = selected_rows[0]
    supporting = selected_rows[1:]

    checklist = expand_checklist(primary, evidence_domains=_evidence_domains(answer_assembly))
    procedure = guided_procedure(primary)

    gaps_coverage = None
    if isinstance(answer_assembly, dict):
        gaps_coverage = ((answer_assembly.get("gaps") or {}).get("coverage"))
        if gaps_coverage is None:
            gaps_coverage = ((answer_assembly.get("confidence") or {}).get("coverage"))

    confidence = score_playbook_confidence(
        playbook=primary,
        checklist=checklist,
        match_score=scored[0][0] if scored else 10,
        gaps_coverage=gaps_coverage,
        framework_overlap=len(fw_set & set(primary.get("frameworks") or [])),
    )

    validation = validate_selection(primary, checklist=checklist)

    explanation = {
        "playbook_id": primary.get("playbook_id"),
        "name": primary.get("name"),
        "reason": _reason_text(primary, primary_reasons, sector=str(sector), framework_ids=framework_ids),
        "match_reasons": primary_reasons,
        "guides_reasoning": True,
        "replaces_reasoning": False,
    }

    return {
        "ok": True,
        "iap_version": IAP_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "playbook_id": primary.get("playbook_id"),
        "playbook_name": primary.get("name"),
        "category": primary.get("category"),
        "sector": sector,
        "intent_v2": intent_v2,
        "question_type": question_type,
        "as_of": as_of,
        "primary": {
            "playbook_id": primary.get("playbook_id"),
            "name": primary.get("name"),
            "category": primary.get("category"),
            "frameworks": primary.get("frameworks"),
            "priority": primary.get("priority"),
        },
        "supporting": [
            {
                "playbook_id": s.get("playbook_id"),
                "name": s.get("name"),
                "category": s.get("category"),
            }
            for s in supporting
        ],
        "playbook_ids": [primary.get("playbook_id")]
        + [s.get("playbook_id") for s in supporting],
        "frameworks_aligned": list(primary.get("frameworks") or []),
        "framework_ids_input": framework_ids,
        "checklist": checklist,
        "procedure": procedure,
        "evidence_required": list(primary.get("evidence_required") or []),
        "knowledge_objects": list(primary.get("knowledge_objects") or []),
        "common_mistakes": list(primary.get("common_mistakes") or []),
        "output_structure": list(primary.get("output_structure") or []),
        "confidence_rules": primary.get("confidence_rules") or {},
        "confidence": confidence,
        "explanation": explanation,
        "validation": validation,
        "dropped_replay": dropped,
        "candidates_scored": len(scored),
        "freeze_locks": FREEZE_LOCKS,
        "llm_used": False,
        "fabricated": False,
        "reasoning_changed": False,
        "guides_reasoning": True,
    }


def _score_playbook(
    pb: dict[str, Any],
    *,
    question_low: str,
    question_type: str,
    intent_v2: str,
    sector: str,
    fw_set: set[str],
    concept_mode: bool,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    # Cue matches (strong) — word-safe for single tokens
    for cue in pb.get("cues") or []:
        if _cue_match(str(cue), question_low):
            score += 25
            reasons.append(f"cue:{cue}")
            if score >= 75:
                break

    # Question type
    qtypes = {str(x).lower() for x in (pb.get("question_types") or [])}
    if question_type and question_type.lower() in qtypes:
        score += 12
        reasons.append(f"question_type:{question_type}")
    if intent_v2 and intent_v2.lower() in qtypes:
        score += 8
        reasons.append(f"intent:{intent_v2}")

    # Sector
    sectors = set(pb.get("sectors") or ["*"])
    if "*" in sectors:
        score += 2
    elif sector in sectors:
        score += 18
        reasons.append(f"sector:{sector}")
    elif sectors and sector not in sectors and "*" not in sectors:
        # Hard mismatch — unless strong cues already hit
        if score < 25:
            return 0, []
        score -= 10
        reasons.append("sector_soft_mismatch")

    # Framework overlap with IFSE
    overlap = fw_set & set(pb.get("frameworks") or [])
    if overlap:
        score += 6 * len(overlap)
        reasons.append(f"frameworks:{','.join(sorted(overlap)[:4])}")

    # Priority soft boost for near-ties
    score += min(int(pb.get("priority") or 0) // 20, 5)

    if concept_mode and pb.get("category") in {"documents", "investment_committee"}:
        score += 3

    return score, reasons


def _fallback_playbook(*, sector: str, fw_set: set[str]) -> dict[str, Any]:
    if sector in {"banks", "nbfc", "insurance"} or "FW_RESIDUAL_INCOME" in fw_set or "FW_PB" in fw_set:
        pb = get_playbook("PB_VAL_BANK_PB_RI")
        if pb:
            return pb
    if "FW_SOTP" in fw_set:
        pb = get_playbook("PB_VAL_SOTP_CONGLOMERATE")
        if pb:
            return pb
    return get_playbook("PB_COMPANY_QUALITY") or list_playbooks()[0]


def _evidence_domains(answer_assembly: dict[str, Any] | None) -> list[str]:
    if not isinstance(answer_assembly, dict):
        return []
    domains: list[str] = []
    for item in ((answer_assembly.get("ordering") or {}).get("ordered")) or []:
        if isinstance(item, dict) and item.get("domain"):
            domains.append(str(item["domain"]))
    for d in ((answer_assembly.get("gaps") or {}).get("present_domains") or []):
        domains.append(str(d))
    return domains


def _reason_text(
    primary: dict[str, Any],
    reasons: list[str],
    *,
    sector: str,
    framework_ids: list[str],
) -> str:
    name = primary.get("name")
    cat = primary.get("category")
    top = ", ".join(reasons[:4]) if reasons else "default"
    fws = ", ".join(framework_ids[:3]) if framework_ids else "none"
    return (
        f"Selected playbook '{name}' ({cat}) for sector={sector} "
        f"with frameworks [{fws}]. Match: {top}. "
        f"Reasoning will follow the analytical checklist; communication renders the procedure."
    )
