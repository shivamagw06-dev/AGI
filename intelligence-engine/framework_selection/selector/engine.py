"""IFSE selector — deterministic multi-framework composition."""

from __future__ import annotations

from typing import Any

from framework_selection.confidence.scorer import score_confidence
from framework_selection.explanation.builder import build_explanation, evidence_union
from framework_selection.mappings.companies import sector_for_company
from framework_selection.mappings.cues import cue_overlays, sector_enrichment
from framework_selection.mappings.questions import INTENT_FRAMEWORKS, QUESTION_TYPE_FRAMEWORKS
from framework_selection.mappings.sectors import SECTOR_FRAMEWORKS, SECTOR_KEYWORDS
from framework_selection.registry.frameworks import get_framework, registry_index
from framework_selection.replay.filter import filter_by_as_of
from framework_selection.rules.forbidden import forbidden_for_sector, is_forbidden
from framework_selection.schema import FREEZE_LOCKS, IFSE_VERSION, MODULE_CODE, PROGRAMME
from framework_selection.validation.gates import validate_selection


_ROLE_RANK = {"primary": 0, "secondary": 1, "supporting": 2}


def select_frameworks(
    *,
    question: str,
    intent_v2: str | None = None,
    question_type: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    ticker_hint: str | None = None,
    concept_mode: bool = False,
    as_of: str | None = None,
    answer_assembly: dict[str, Any] | None = None,
    evidence_types_present: list[str] | None = None,
) -> dict[str, Any]:
    """Select institutional frameworks after Answer Assembly, before reasoning."""
    sector, sector_source = _detect_sector(
        question=question,
        entities=entities or [],
        ticker_hint=ticker_hint,
        concept_mode=concept_mode,
    )

    composed: dict[str, dict[str, Any]] = {}
    # Always surface sector forbids for audit (even if never proposed)
    forbidden_rejected: list[str] = list(forbidden_for_sector(sector))

    def _add(fid: str, role: str, source: str) -> None:
        if is_forbidden(fid, sector=sector):
            if fid not in forbidden_rejected:
                forbidden_rejected.append(fid)
            return
        meta = get_framework(fid)
        if not meta:
            return
        prev = composed.get(fid)
        if prev is None or _ROLE_RANK.get(role, 9) < _ROLE_RANK.get(str(prev.get("role")), 9):
            composed[fid] = {
                "framework_id": fid,
                "name": meta.get("name"),
                "role": role,
                "source": source,
                "purpose": meta.get("purpose"),
            }

    # Sector composition
    for fid, role in SECTOR_FRAMEWORKS.get(sector) or SECTOR_FRAMEWORKS["generic"]:
        _add(fid, role, f"sector:{sector}")

    # Intent overlays
    for fid, role in INTENT_FRAMEWORKS.get(intent_v2 or "") or []:
        _add(fid, role, f"intent:{intent_v2}")

    # Question-type overlays
    for fid, role in QUESTION_TYPE_FRAMEWORKS.get((question_type or "").lower()) or []:
        _add(fid, role, f"question_type:{question_type}")

    # Valuation expensive / cheap cue → historical + ROE for banks
    low = (question or "").lower()
    if any(k in low for k in ("expensive", "cheap", "premium", "undervalued", "overvalued")):
        _add("FW_HISTORICAL_VALUATION", "secondary", "cue:valuation_language")
        if sector in {"banks", "nbfc", "insurance"}:
            _add("FW_ROE", "supporting", "cue:valuation_language")
            _add("FW_MACRO_TRANSMISSION", "supporting", "cue:valuation_language")

    # Sprint 3.3 — question-cue overlays (risk / documents / ops) + sector enrichment
    for fid, role, src in cue_overlays(question or ""):
        _add(fid, role, src)
    for fid, role, src in sector_enrichment(sector):
        _add(fid, role, src)

    selected = sorted(
        composed.values(),
        key=lambda r: (_ROLE_RANK.get(str(r.get("role")), 9), str(r.get("framework_id"))),
    )

    # Replay filter
    registry = registry_index()
    selected, dropped_replay = filter_by_as_of(selected, as_of=as_of, registry=registry)

    if not selected:
        _add("FW_NONE", "primary", "fallback")
        selected = list(composed.values())
        selected, dropped_replay2 = filter_by_as_of(selected, as_of=as_of, registry=registry)
        dropped_replay = list(set(dropped_replay + dropped_replay2))

    gaps_coverage = None
    if isinstance(answer_assembly, dict):
        gaps_coverage = ((answer_assembly.get("gaps") or {}).get("coverage"))
        if gaps_coverage is None:
            gaps_coverage = ((answer_assembly.get("confidence") or {}).get("coverage"))

    confidence = score_confidence(
        selected=selected,
        sector=sector,
        sector_source=sector_source,
        intent_v2=intent_v2,
        evidence_domains=None,
        gaps_coverage=gaps_coverage,
        as_of=as_of,
        forbidden_rejected=forbidden_rejected,
    )

    req_evidence = evidence_union(selected)
    explanation = build_explanation(
        selected=selected,
        sector=sector,
        sector_source=sector_source,
        intent_v2=intent_v2,
        confidence=confidence,
        forbidden_rejected=forbidden_rejected,
        evidence_required=req_evidence,
        evidence_present=evidence_types_present,
    )

    validation = validate_selection(
        selected=selected,
        sector=sector,
        confidence=confidence,
        dropped_replay=dropped_replay,
    )

    primary = [r for r in selected if r.get("role") == "primary"]
    secondary = [r for r in selected if r.get("role") == "secondary"]
    supporting = [r for r in selected if r.get("role") == "supporting"]

    return {
        "ok": bool(validation.get("passed")),
        "ifse_version": IFSE_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "sector": sector,
        "sector_source": sector_source,
        "intent_v2": intent_v2,
        "question_type": question_type,
        "as_of": as_of,
        "concept_mode": concept_mode,
        "selected": selected,
        "primary": primary,
        "secondary": secondary,
        "supporting": supporting,
        "framework_ids": [r.get("framework_id") for r in selected],
        "forbidden_rejected": forbidden_rejected,
        "dropped_replay": dropped_replay,
        "confidence": confidence,
        "explanation": explanation,
        "validation": validation,
        "required_evidence": req_evidence,
        "multi_framework": len(selected) > 1,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "llm_used": False,
        "reasoning_changed": False,
        "governance_changed": False,
    }


def _detect_sector(
    *,
    question: str,
    entities: list[dict[str, Any]],
    ticker_hint: str | None,
    concept_mode: bool,
) -> tuple[str, str]:
    # Company map first (even in concept mode if question names a sector company for education)
    tickers: list[str] = []
    for e in entities:
        if e.get("type") == "company" and e.get("id"):
            tickers.append(str(e["id"]).upper())
    if ticker_hint and not concept_mode:
        tickers.append(str(ticker_hint).upper())

    for t in tickers:
        sec = sector_for_company(t)
        if sec:
            return sec, f"company:{t}"

    # Keyword / concept sector
    low = (question or "").lower()
    best: str | None = None
    best_hits = 0
    for sector, kws in SECTOR_KEYWORDS.items():
        hits = sum(1 for k in kws if k in low)
        if hits > best_hits:
            best_hits = hits
            best = sector
    if best and best_hits > 0:
        return best, "keyword"

    return "generic", "default"
