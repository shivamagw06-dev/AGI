"""Weighted coverage score by required evidence class."""

from __future__ import annotations

from typing import Any, Dict, Optional

from institutional_coverage_factory.schema import EVIDENCE_CLASSES


def _dtype_set(registry_items: list) -> set[str]:
    return {str(i.get("document_type") or "") for i in (registry_items or [])}


def _class_present(
    class_id: str,
    *,
    checks: Dict[str, bool],
    dtypes: set[str],
    pack: Dict[str, Any],
    meta: Dict[str, Any],
) -> bool:
    keys = meta.get("phase1_keys") or ()
    if keys:
        if any(bool(checks.get(k)) for k in keys):
            return True
    for dt in meta.get("document_types") or ():
        if dt in dtypes:
            return True

    if class_id == "financial_statements":
        fin = pack.get("financials") or {}
        return bool(fin.get("published") and (fin.get("periods") or []))
    if class_id == "management_guidance":
        # Soft: guidance doc type or earnings guidance field
        if "management_guidance" in dtypes or "guidance" in dtypes:
            return True
        earn = pack.get("earnings") or {}
        return bool(earn.get("guidance") or earn.get("management_guidance"))
    if class_id == "company_memory":
        mem = pack.get("company_memory") or {}
        return (mem.get("slot_coverage") or 0) >= 0.25 or bool(mem.get("populated"))
    if class_id == "knowledge_graph":
        return bool(pack.get("knowledge_graph"))
    if class_id == "segment_kpis":
        fin = pack.get("financials") or {}
        return bool(fin.get("segment_revenue") or checks.get("segment_history"))
    return False


def score_evidence_classes(
    ticker: str,
    *,
    pack: Optional[Dict[str, Any]] = None,
    phase1: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    p = pack
    if p is None:
        try:
            from institutional_evidence.research_pack.builder import build_institutional_research_pack

            p = build_institutional_research_pack(t)
        except Exception:
            p = {}
    p = p if isinstance(p, dict) else {}

    ph = phase1
    if ph is None:
        try:
            from institutional_evidence.phase1_acceptance import evaluate_institutional_coverage

            ph = evaluate_institutional_coverage(t, pack=p)
        except Exception:
            ph = {}
    ph = ph if isinstance(ph, dict) else {}
    checks = ph.get("checks") or {}

    reg_items = ((p.get("evidence") or {}).get("registry") or {}).get("items") or []
    dtypes = _dtype_set(reg_items)

    classes: Dict[str, Any] = {}
    earned = 0.0
    total_weight = 0.0
    missing: list[str] = []

    for class_id, meta in EVIDENCE_CLASSES.items():
        weight = float(meta["weight"])
        total_weight += weight
        present = _class_present(class_id, checks=checks, dtypes=dtypes, pack=p, meta=meta)
        classes[class_id] = {
            "present": present,
            "required": bool(meta.get("required")),
            "weight": weight,
            "collector": meta.get("collector"),
        }
        if present:
            earned += weight
        elif meta.get("required"):
            missing.append(class_id)

    coverage_pct = round(100.0 * earned / max(1.0, total_weight), 2)
    return {
        "ok": True,
        "ticker": t,
        "coverage_pct": coverage_pct,
        "earned_weight": earned,
        "total_weight": total_weight,
        "classes": classes,
        "missing_classes": missing,
        "phase1_pass_pct": ph.get("pass_pct"),
        "institutional_coverage_complete_phase1": bool(
            ph.get("institutional_coverage_complete")
        ),
    }


def coverage_score_for(ticker: str) -> Dict[str, Any]:
    return score_evidence_classes(ticker)
