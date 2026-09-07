"""Merge ECP completions into LEO package + CID — fill empties only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from ecp.schema import ECP_VERSION
from leo.gates import assess_quality_gate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_evidence_objects(
    existing: List[Dict[str, Any]],
    new_objects: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Append new evidence types only when type was missing (or same type with higher confidence empty fields)."""
    present_types: Set[str] = {
        str(o.get("evidence_type")) for o in existing or [] if isinstance(o, dict) and o.get("evidence_type")
    }
    seen_ids = {str(o.get("evidence_id")) for o in existing or [] if isinstance(o, dict)}
    out = list(existing or [])
    for obj in new_objects or []:
        if not isinstance(obj, dict):
            continue
        eid = str(obj.get("evidence_id") or "")
        et = str(obj.get("evidence_type") or "")
        if eid and eid in seen_ids:
            continue
        # Prefer filling missing types; also allow additional facts for same type from ECP
        if et and et not in present_types:
            out.append(obj)
            present_types.add(et)
            if eid:
                seen_ids.add(eid)
        elif et and obj.get("metadata", {}).get("completed_by") == "ecp":
            # Same type already present — only add if not duplicate source fact
            out.append(obj)
            if eid:
                seen_ids.add(eid)
    return out


def reassess_leo_package(leo_pkg: Dict[str, Any], merged_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Recompute LEO quality gate after ECP merge — does not redesign LEO."""
    pkg = dict(leo_pkg or {})
    plan = dict(pkg.get("evidence_plan") or pkg.get("plan") or {})
    present_types = {o.get("evidence_type") for o in merged_objects if isinstance(o, dict)}
    required = list(plan.get("required_evidence") or [])
    if required:
        plan["missing_evidence"] = [t for t in required if t not in present_types]
        plan["present_evidence"] = sorted(t for t in present_types if t)
    usage = dict(pkg.get("usage") or {})
    # Mark external contribution when ECP completed via market providers
    if any((o.get("source_id") in {"yahoo", "dvc", "market_data_client", "indianapi", "finnhub", "fmp"}) for o in merged_objects):
        usage["external_api_contributed"] = True
    if any((o.get("metadata") or {}).get("completed_by") == "ecp" for o in merged_objects):
        usage["ecp_completed"] = True
    gate = assess_quality_gate(plan, merged_objects, usage)
    pkg["evidence_objects"] = merged_objects
    pkg["evidence_plan"] = plan
    pkg["plan"] = plan
    pkg["usage"] = usage
    pkg["quality_gate"] = gate
    pkg["sif_evidence_supplied"] = gate.get("sif_evidence_supplied") or pkg.get("sif_evidence_supplied") or {}
    pkg["missing_evidence"] = gate.get("missing_evidence") or plan.get("missing_evidence") or []
    return pkg


def apply_cid_enrichment(
    ticker: str,
    dossier: Dict[str, Any],
    *,
    yahoo_pack: Dict[str, Any] | None = None,
    dvc_pack: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Soft-merge Yahoo + DVC into CID (fill empties); persist via CID store."""
    from cid.coverage import compute_coverage
    from cid.store import get_cid_store

    d = dict(dossier or {})
    t = (ticker or d.get("ticker") or "").upper()

    if yahoo_pack and yahoo_pack.get("enabled"):
        try:
            from yfp.enrich import merge_yahoo_into_dossier

            d = merge_yahoo_into_dossier(d, yahoo_pack)
        except Exception:
            pass

    if dvc_pack and (dvc_pack.get("enabled") or dvc_pack.get("validated_fields")):
        try:
            from dvc.enrich import merge_dvc_into_dossier

            d = merge_dvc_into_dossier(d, dvc_pack)
        except Exception:
            pass

    cov = compute_coverage(d)
    d.update(
        {
            "coverage": cov["coverage"],
            "coverage_score": cov["coverage_score"],
            "coverage_grade": cov["coverage_grade"],
            "missing_evidence": cov["missing_evidence"],
            "updated_at": _now(),
        }
    )
    d.setdefault("enrichment", {})
    d["enrichment"]["ecp"] = {
        "ecp_version": ECP_VERSION,
        "completed_at": _now(),
        "yahoo": bool(yahoo_pack and yahoo_pack.get("enabled")),
        "dvc": bool(dvc_pack and (dvc_pack.get("validated_fields") or dvc_pack.get("enabled"))),
    }
    if t:
        try:
            d = get_cid_store().put(d)
        except Exception:
            pass
    return d


def quality_panel(
    *,
    gaps_before: Dict[str, Any],
    gaps_after: Dict[str, Any],
    leo_pkg: Dict[str, Any],
    cid: Dict[str, Any],
    coverage_before: float,
    coverage_after: float,
) -> Dict[str, Any]:
    """Quality gates display payload for Ask AGI / admin."""
    dvc_panel = cid.get("data_quality_panel") or (cid.get("dvc") or {}).get("panel") or {}
    gate = leo_pkg.get("quality_gate") or {}
    return {
        "coverage_pct": round(coverage_after * 100, 1),
        "coverage_before_pct": round(coverage_before * 100, 1),
        "research_grade": dvc_panel.get("research_grade") or cid.get("research_grade") or cid.get("coverage_grade"),
        "data_grade": dvc_panel.get("data_grade") or cid.get("data_grade"),
        "knowledge_grade": dvc_panel.get("knowledge_grade") or cid.get("knowledge_grade"),
        "missing_items": [x.get("item") for x in (gaps_after.get("flat_missing") or [])][:20],
        "missing_leo": gaps_after.get("leo_missing") or [],
        "must_have_missing": gate.get("must_have_missing") or [],
        "confidence": dvc_panel.get("confidence"),
        "freshness": dvc_panel.get("freshness"),
        "gate_blocked": bool(gate.get("blocked")),
        "gate_allow": bool(gate.get("allow_recommendation")),
        "quality_improvement_pct": round((coverage_after - coverage_before) * 100, 1),
        "ecp_version": ECP_VERSION,
    }


def withheld_explanation(panel: Dict[str, Any], gaps: Dict[str, Any]) -> str:
    """Professional explanation when recommendation remains withheld.

    Soft-wire: never expose raw snake_case checklist keys to Ask AGI clients.
    Full research briefing is still produced — this text is for recommendation status only.
    """
    missing = panel.get("missing_items") or []
    leo_miss = panel.get("must_have_missing") or panel.get("missing_leo") or []
    shown = list(dict.fromkeys([*leo_miss, *missing]))[:12]
    if not shown:
        shown = list(gaps.get("leo_missing") or [])[:8] or ["validated institutional evidence"]

    try:
        from answer_construction.knowledge_gaps import professional_gap

        gap_lines = [professional_gap(m) for m in shown]
    except Exception:
        gap_lines = [
            str(m).replace("_", " ").strip().capitalize() + " coverage is still being completed."
            for m in shown
        ]

    # Deduplicate while preserving order
    gap_lines = list(dict.fromkeys([g for g in gap_lines if g]))[:8]
    cov = panel.get("coverage_pct")
    cov_bit = f" Current validated coverage is about {cov}%." if cov is not None else ""

    lines = [
        "Institutional recommendation status: withheld." + cov_bit,
        "Current evidence is insufficient to support a Buy / Hold / Sell recommendation, "
        "but the research briefing itself should still be read in full.",
        "Current knowledge gaps:",
    ]
    for g in gap_lines:
        lines.append(f"- {g}")
    lines.append(
        "AGI continues evidence completion against the living dossier; recommendation readiness "
        "reopens when institutional coverage clears the bar."
    )
    return "\n".join(lines)
