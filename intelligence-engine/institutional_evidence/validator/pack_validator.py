"""Research Pack Validator — BLOCK if mandatory components fail. Never draft around gaps."""

from __future__ import annotations

from typing import Any, Dict, List

from ..schema import (
    BLOCKED_RECOMMENDATIONS,
    FRESHNESS_MAX_DAYS,
    FORBIDDEN_INVENTED_FIELDS,
    MANDATORY_PACK_COMPONENTS,
    RESEARCH_READY_THRESHOLD,
)


def _fin_ok(financials: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    periods = financials.get("periods") or []
    if not periods or financials.get("zero_periods"):
        reasons.append("canonical_statements_zero_periods")
    if not financials.get("published"):
        reasons.append("canonical_statements_not_published")
    # Accounting identity soft checks on latest period with both sides
    for p in periods[:3]:
        if not isinstance(p, dict):
            continue
        inc = p.get("income_statement") or {}
        rev, ebitda = inc.get("revenue"), inc.get("ebitda")
        if rev is not None and ebitda is not None and rev != 0:
            if abs(float(ebitda)) > abs(float(rev)) * 1.5:
                reasons.append(f"accounting_identity_suspect:{p.get('period')}")
    return len(reasons) == 0, reasons


def _evidence_ok(evidence: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    reg = evidence.get("registry") or {}
    items = reg.get("items") or evidence.get("items") or []
    if not items:
        reasons.append("evidence_registry_empty")
    missing_hash = [i for i in items if isinstance(i, dict) and not i.get("hash")]
    if missing_hash:
        reasons.append("evidence_hash_missing")
    stale = [
        i
        for i in items
        if isinstance(i, dict)
        and i.get("freshness_ok") is False
        and (i.get("freshness_days") or 0) > FRESHNESS_MAX_DAYS
    ]
    if stale and not any(i.get("research_ready") for i in items if isinstance(i, dict)):
        reasons.append("evidence_freshness_exceeded")
    return len(reasons) == 0, reasons


def _decision_consistent(pack: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    decision = pack.get("decision") or {}
    rec = str(
        decision.get("recommendation")
        or decision.get("action")
        or decision.get("rating")
        or ""
    ).upper().strip()
    claim_safe = bool(pack.get("claim_safe"))
    ready = bool((pack.get("research_readiness") or {}).get("research_ready") or pack.get("research_ready"))
    if rec in BLOCKED_RECOMMENDATIONS and not (claim_safe and ready):
        # During validation claim_safe may not be set yet — use financials/evidence
        fin_ok, _ = _fin_ok(pack.get("financials") or {})
        ev_ok, _ = _evidence_ok(pack.get("evidence") or {})
        if not (fin_ok and ev_ok):
            reasons.append(f"recommendation_contradiction:{rec}_without_evidence")
    return len(reasons) == 0, reasons


def validate_research_pack_dict(pack: Dict[str, Any]) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    failures: List[str] = []

    for comp in MANDATORY_PACK_COMPONENTS:
        present = pack.get(comp) is not None
        checks[f"component_{comp}"] = present
        if not present:
            failures.append(f"missing_component:{comp}")

    fin_ok, fin_reasons = _fin_ok(pack.get("financials") or {})
    checks["financial_statements"] = fin_ok
    failures.extend(fin_reasons)

    ev_ok, ev_reasons = _evidence_ok(pack.get("evidence") or {})
    checks["evidence_completeness"] = ev_ok
    failures.extend(ev_reasons)

    mem = pack.get("company_memory") or {}
    mem_ok = bool(mem.get("ok")) and (mem.get("slot_coverage") or 0) >= 0.15
    checks["company_memory"] = mem_ok
    if not mem_ok:
        failures.append("company_memory_thin")

    readiness = pack.get("research_readiness") or {}
    score = float(readiness.get("score") or readiness.get("readiness_score") or 0)
    checks["readiness_threshold"] = score >= RESEARCH_READY_THRESHOLD or bool(
        readiness.get("research_ready")
    )
    # Readiness is a publishing gate — tracked separately from claim_safe
    publish_failures: List[str] = []
    if readiness and not checks["readiness_threshold"]:
        publish_failures.append("research_readiness_below_threshold")

    lineage = bool((pack.get("evidence") or {}).get("primary_citation_ids"))
    checks["lineage"] = lineage
    if not lineage:
        failures.append("lineage_missing_primary_citations")

    dec_ok, dec_reasons = _decision_consistent(pack)
    checks["recommendation_consistency"] = dec_ok
    failures.extend(dec_reasons)

    # Claim safety: statements published + evidence + numbers + lineage
    # (does not require readiness threshold — that gates publication)
    financials = pack.get("financials") or {}
    has_numbers = False
    for p in (financials.get("periods") or [])[:1]:
        inc = (p or {}).get("income_statement") or {}
        if any(inc.get(k) is not None for k in ("revenue", "pat", "ebitda", "eps")):
            has_numbers = True
    claim_blockers = [
        f
        for f in failures
        if not f.startswith("recommendation_contradiction")
    ]
    claim_safe = bool(fin_ok and ev_ok and has_numbers and lineage and not claim_blockers)

    checks["claim_safety"] = claim_safe
    checks["sector_validation"] = bool(pack.get("sector"))

    all_failures = failures + publish_failures
    blocked = bool(all_failures) or not claim_safe
    return {
        "ok": not blocked,
        "claim_safe": claim_safe,
        "blocked": blocked,
        "failures": all_failures,
        "checks": checks,
        "forbidden_invented_fields": list(FORBIDDEN_INVENTED_FIELDS),
        "rule": "If any mandatory component fails — BLOCK. Never draft around missing data.",
        "evidence_unavailable_message": "Evidence unavailable.",
    }


def ci_gate_failures(pack: Dict[str, Any]) -> List[str]:
    """CI Gates — fail build conditions from the master programme."""
    v = validate_research_pack_dict(pack)
    gates: List[str] = []
    fin = pack.get("financials") or {}
    if not (fin.get("periods") or []) or fin.get("zero_periods"):
        gates.append("CI: Canonical statements contain zero periods")
    for f in v.get("failures") or []:
        if "accounting_identity" in f:
            gates.append(f"CI: Accounting identities fail ({f})")
        if "evidence_hash_missing" in f:
            gates.append("CI: Evidence hash missing")
        if "freshness" in f:
            gates.append("CI: Freshness exceeded")
        if "missing_component" in f:
            gates.append(f"CI: Research Pack incomplete ({f})")
        if "recommendation_contradiction" in f:
            gates.append(f"CI: Recommendation contradiction detected ({f})")
    if pack.get("research_generated") and not pack.get("claim_safe"):
        gates.append("CI: Research generated with missing mandatory evidence")
    return gates
