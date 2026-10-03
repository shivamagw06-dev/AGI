"""Deterministic Institutional Decision Office.

Separates Analysis (thesis) from Decision. Emits institutional process decisions
— Wait / Monitor / Increase Research / Reject / Escalate / Approve /
Review After … — never orders or BUY/SELL execution.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from institutional_decision_office import store as decision_store
from institutional_decision_office.schema import (
    DECISION_SCHEMA_VERSION,
    DECISION_TYPES,
    FORBIDDEN_DECISIONS,
    FREEZE_LOCKS,
    IDO_VERSION,
    OWNER,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _review_date(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def _bump_version(prev: dict[str, Any] | None) -> str:
    if not prev:
        return "1.0"
    ver = str(prev.get("version") or "1.0")
    try:
        major, minor = ver.split(".", 1)
        return f"{int(major)}.{int(minor) + 1}"
    except Exception:
        return "1.1"


def _thesis_doc(investment_thesis: dict[str, Any] | None) -> dict[str, Any]:
    pack = investment_thesis or {}
    return dict(pack.get("thesis") or pack)


def _committee_tilt(icr: dict[str, Any], thesis: dict[str, Any]) -> str | None:
    preferred = thesis.get("preferred_case") or icr.get("preferred_case")
    if preferred in {"bull", "base", "bear"}:
        return str(preferred)
    return None


def _decide(
    *,
    thesis: dict[str, Any],
    icr: dict[str, Any],
    icc: dict[str, Any],
) -> tuple[str, str, list[str], list[str], str, str, int]:
    """
    Return (decision, reason, required_conditions, dependencies,
            review_trigger, lifecycle_status, review_days).
    """
    conf = thesis.get("confidence")
    if conf is None:
        conf = (icc.get("report") or {}).get("overall_confidence")
    try:
        conf_f = float(conf) if conf is not None else 50.0
    except (TypeError, ValueError):
        conf_f = 50.0

    conf_change = thesis.get("confidence_change")
    try:
        drop = float(conf_change) if conf_change is not None else 0.0
    except (TypeError, ValueError):
        drop = 0.0

    preferred = _committee_tilt(icr, thesis)
    monitoring = " ".join(str(x) for x in (thesis.get("monitoring_checklist") or [])).lower()
    missing = str(thesis.get("what_market_missing") or "").lower()
    n_cases = int(icr.get("n_cases") or 0)
    outcome = (icr.get("report") or {}).get("outcome") or ""
    view = str(thesis.get("investment_view") or "").lower()

    deps = [
        f"thesis:{thesis.get('thesis_id')}",
        f"thesis_version:{thesis.get('version')}",
    ]
    if preferred:
        deps.append(f"committee_preferred:{preferred}")
    deps.append(f"confidence:{int(round(conf_f))}")

    # 1) Insufficient / reject weak analysis
    if outcome == "insufficient_evidence" or n_cases == 0:
        return (
            "Reject",
            "Decision: Reject progression — insufficient evidence for an institutional investment decision. "
            "Analysis remains available as Watch thesis only.",
            ["Obtain evidence sufficient for at least one viable committee case"],
            deps,
            "Evidence refresh",
            "Closed",
            90,
        )

    # 2) Sharp confidence drop → escalate / review
    if drop <= -10.0:
        return (
            "Escalate",
            f"Decision: Escalate — thesis confidence fell {abs(drop):g} points "
            f"(now {int(round(conf_f))}/100). Analysis may still be constructive; "
            "decision office requires elevated review before any commitment path.",
            ["Committee re-deliberation", "Reconfirm invalidation conditions"],
            deps,
            "Confidence drop > 10 points",
            "Committee Review",
            14,
        )

    # 3) Committee preferred bear with low/moderate confidence
    if preferred == "bear" and conf_f < 75:
        return (
            "Wait",
            "Decision: Wait — committee preferred case is Bear and confidence is not high. "
            "Positive research curiosity does not imply action; valuation/downside balance argues for patience.",
            ["Bear case invalidation must clear", "Confidence recover above 75"],
            deps,
            "Committee shift away from Bear",
            "Watch",
            45,
        )

    # 4) Earnings / results review triggers from monitoring
    if "earnings" in monitoring or "earnings" in missing:
        return (
            "Review After Earnings",
            "Decision: Review After Earnings — thesis monitoring checklist awaits the next earnings release. "
            "No buy/sell; institutional process defers commitment until results update confidence and cases.",
            ["Next earnings release published", "Post-print committee case refresh"],
            deps,
            "Next earnings release",
            "Research",
            45,
        )

    if "budget" in monitoring or "budget" in missing:
        return (
            "Review After Budget",
            "Decision: Review After Budget — material fiscal/budget dependency flagged. "
            "Hold institutional posture until budget clarity updates the thesis.",
            ["Budget / policy outcome available"],
            deps,
            "Budget announcement",
            "Research",
            60,
        )

    if "result" in monitoring and "earnings" not in monitoring:
        return (
            "Review After Results",
            "Decision: Review After Results — thesis awaits a material results catalyst before decision progression.",
            ["Material results event"],
            deps,
            "Results event",
            "Research",
            45,
        )

    # 5) Critical missing evidence → increase research
    await_evidence = any("await evidence" in str(x).lower() for x in (thesis.get("monitoring_checklist") or []))
    guidance_gap = "guidance" in missing and "no critical" not in missing
    if await_evidence or guidance_gap or conf_f < 55:
        return (
            "Increase Research",
            "Decision: Increase Research — analysis gaps (missing evidence / modest confidence) "
            "prevent institutional approval. Expand evidence before any progressive decision.",
            list(thesis.get("monitoring_checklist") or [])[:4]
            or ["Fill critical missing evidence items"],
            deps,
            "Missing evidence filled",
            "Research",
            30,
        )

    # 6) Strong bull/base + high confidence → approve (process approval, not trade)
    if preferred in {"bull", "base"} and conf_f >= 80 and drop > -5:
        return (
            "Approve",
            "Decision: Approve — thesis quality and confidence clear institutional bar for "
            "continued active monitoring under Decision Office governance. "
            "This is process approval, not an order to buy or sell.",
            ["Maintain monitoring checklist", "Re-review on confidence drop > 10"],
            deps,
            "Ongoing monitoring cadence",
            "Approved",
            30,
        )

    # 7) Constructive but not bar-clearing → monitor
    if preferred in {"bull", "base"} and conf_f >= 65:
        return (
            "Monitor",
            "Decision: Monitor — analysis is constructive and committee balance supports the base/upside case, "
            "but confidence or separation is not yet sufficient for Approve. Keep under active watch.",
            ["Confidence sustain ≥ 65", "No committee flip to Bear"],
            deps,
            "Monthly thesis review",
            "Monitoring",
            30,
        )

    # 8) Default institutional posture
    _ = view  # reserved for future lexical cues
    return (
        "Wait",
        "Decision: Wait — default institutional posture. Analysis may continue; "
        "Decision Office does not equate a positive thesis with immediate action.",
        ["Clearer committee separation", "Higher calibrated confidence"],
        deps,
        "Thesis update",
        "Watch",
        30,
    )


def deliberate_decision(
    *,
    question: str,
    investment_thesis: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    thesis = _thesis_doc(investment_thesis)
    icr = committee_reasoning or {}
    icc = confidence_calibration or {}
    _ = hypothesis_evaluation  # available for future separation metrics; frozen consume-only

    thesis_id = str(thesis.get("thesis_id") or "TH-UNKNOWN")
    company = thesis.get("company")
    ticker = thesis.get("ticker")

    decision, reason, conditions, deps, trigger, lifecycle, review_days = _decide(
        thesis=thesis, icr=icr, icc=icc
    )
    if decision not in DECISION_TYPES:
        decision = "Wait"
    if decision in FORBIDDEN_DECISIONS:
        decision = "Wait"

    conf = thesis.get("confidence")
    if conf is None:
        conf = (icc.get("report") or {}).get("overall_confidence")

    # Stable id per thesis+decision type; version bumps on revisit
    decision_id = decision_store.make_decision_id(thesis_id, decision)
    prev = decision_store.get(decision_id) or decision_store.get_by_thesis(thesis_id)
    # If prior decision for thesis differs in type, new id; still track update on same thesis
    is_update = bool(prev and prev.get("decision_id") == decision_id)
    if prev and prev.get("decision_id") != decision_id:
        # Closing prior path is recorded via new object; keep version fresh
        is_update = False
        prev_for_version = None
    else:
        prev_for_version = prev

    version = _bump_version(prev_for_version) if is_update else "1.0"

    decision_obj = {
        "decision_id": decision_id,
        "thesis_id": thesis_id,
        "company": company,
        "ticker": ticker,
        "decision": decision,
        "reason": reason,
        "required_conditions": conditions[:8],
        "dependencies": deps,
        "confidence": conf,
        "confidence_reason": thesis.get("confidence_reason")
        or (icc.get("report") or {}).get("confidence_reason"),
        "owner": OWNER,
        "review_date": _review_date(review_days),
        "review_trigger": trigger,
        "status": lifecycle,
        "lifecycle": lifecycle,
        "version": version,
        "schema_version": DECISION_SCHEMA_VERSION,
        "ido_version": IDO_VERSION,
        "analysis_decision_separated": True,
        "thesis_investment_view": thesis.get("investment_view"),
        "thesis_decision_status": thesis.get("decision_status"),
        "committee_preferred_case": thesis.get("preferred_case") or icr.get("preferred_case"),
        "orders": None,
        "execution": False,
        "buy_sell": None,
        "question": question,
        "as_of": as_of,
        "last_updated": _utc_now(),
        "created_at": (prev_for_version or {}).get("created_at") or _utc_now(),
        "provenance": {
            "ite_version": thesis.get("ite_version") or (investment_thesis or {}).get("ite_version"),
            "thesis_version": thesis.get("version"),
            "icr_version": icr.get("icr_version"),
            "icc_version": icc.get("icc_version"),
        },
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "judgment_stack_modified": False,
        "thesis_modified": False,
        "freeze_locks": dict(FREEZE_LOCKS),
        "metadata": dict(metadata or {}),
    }

    pack = {
        "ido_version": IDO_VERSION,
        "schema_version": DECISION_SCHEMA_VERSION,
        "decision": decision_obj,
        "decision_id": decision_id,
        "persisted": False,
        "guides_decision": True,
        "reasoning_changed": False,
        "judgment_changed": False,
        "thesis_changed": False,
        "orders_emitted": False,
        "buy_sell_emitted": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }

    if persist:
        saved = decision_store.upsert(decision_obj, is_update=is_update)
        pack["decision"] = saved
        pack["persisted"] = True

    return pack
