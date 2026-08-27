"""Deterministic Institutional Learning Office.

Process memory from closed/observed investment work — never rewrites thesis history
and never updates Knowledge Factory market facts.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from institutional_learning_office import store as learning_store
from institutional_learning_office.schema import (
    FREEZE_LOCKS,
    ILO_VERSION,
    LEARNING_CATEGORIES,
    LEARNING_SCHEMA_VERSION,
    OUTCOME_LABELS,
    OWNER,
    ROOT_CAUSE_BUCKETS,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _thesis(pack: dict[str, Any] | None) -> dict[str, Any]:
    p = pack or {}
    return dict(p.get("thesis") or p)


def _decision(pack: dict[str, Any] | None) -> dict[str, Any]:
    p = pack or {}
    return dict(p.get("decision") or p)


def _idea(pack: dict[str, Any] | None) -> dict[str, Any]:
    p = pack or {}
    return dict(p.get("idea") or p)


def _events(pack: dict[str, Any] | None) -> list[dict[str, Any]]:
    p = pack or {}
    rows = p.get("events") or []
    return [e for e in rows if isinstance(e, dict)]


def _learning_id(thesis_id: str, decision_id: str, nonce: str) -> str:
    raw = f"{thesis_id}|{decision_id}|{nonce}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"IL-{digest}"


def _blob(*parts: Any) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def _classify_category(
    *,
    question: str,
    thesis: dict[str, Any],
    decision: dict[str, Any],
    events: list[dict[str, Any]],
    root_cause: str,
) -> str:
    text = _blob(
        question,
        thesis.get("investment_view"),
        decision.get("decision"),
        root_cause,
        [e.get("recommended_action") for e in events],
        [((e.get("trigger") or {}) if isinstance(e.get("trigger"), dict) else {}).get("code") for e in events],
    )
    rules: list[tuple[tuple[str, ...], str]] = [
        (("confidence", "monitoring", "guidance withdrawn", "results published"), "Monitoring"),
        (("committee", "bull case", "bear case", "deliberation"), "Committee"),
        (("hypothesis", "invalidat"), "Hypothesis"),
        (("framework", "playbook"), "Framework"),
        (("evidence", "filing", "source quality"), "Evidence"),
        (("portfolio", "relative rank", "role", "conviction"), "Portfolio"),
        (("timing", "too early", "too late", "catalyst timing"), "Timing"),
        (("macro", "rates", "fx", "inflation", "gdp", "demand"), "Macro"),
        (("risk", "drawdown", "correlation", "concentration"), "Risk"),
        (("decision", "wait", "reject", "approve", "escalate"), "Decision"),
    ]
    for keywords, cat in rules:
        if any(k in text for k in keywords):
            return cat if cat in LEARNING_CATEGORIES else "Decision"
    if root_cause in LEARNING_CATEGORIES:
        return root_cause
    return "Decision"


def _root_cause(
    *,
    question: str,
    thesis: dict[str, Any],
    decision: dict[str, Any],
    events: list[dict[str, Any]],
) -> str:
    text = _blob(question, thesis.get("investment_view"), [e.get("explanation") for e in events])
    mapping: list[tuple[tuple[str, ...], str]] = [
        (("pricing pressure", "price competition", "ASP", "discounting"), "Management"),
        (("margin expansion", "operating margin", "cost"), "Evidence"),
        (("guidance", "management commentary", "ceo", "cfo"), "Management"),
        (("valuation", "multiple", "de-rate", "rerating"), "Valuation"),
        (("macro", "rates", "discretionary demand", "global demand"), "Macro"),
        (("catalyst", "event", "results published"), "Catalyst"),
        (("timing", "too early", "too late"), "Timing"),
        (("execution", "order", "position", "broker"), "Execution"),
        (("evidence", "filing", "missing data"), "Evidence"),
        (("hypothesis", "bull invalid"), "Hypothesis"),
        (("decision", "process"), "Decision Process"),
    ]
    for keywords, bucket in mapping:
        if any(k in text for k in keywords):
            return bucket if bucket in ROOT_CAUSE_BUCKETS else "Unknown"
    # Prefer monitoring-driven root cause
    for e in events:
        if e.get("requires_review"):
            code = str(((e.get("trigger") or {}) if isinstance(e.get("trigger"), dict) else {}).get("code") or "")
            if "guidance" in code:
                return "Management"
            if "confidence" in code:
                return "Evidence"
            if "results" in code:
                return "Catalyst"
            if "bull" in code:
                return "Hypothesis"
    return "Unknown"


def _outcome(
    *,
    thesis: dict[str, Any],
    decision: dict[str, Any],
    events: list[dict[str, Any]],
) -> str:
    lifecycle = str(thesis.get("lifecycle") or thesis.get("status") or "")
    dec = str(decision.get("decision") or "")
    review_n = sum(1 for e in events if e.get("requires_review"))
    if lifecycle in {"Closed", "Archived"} or dec == "Reject":
        # Closed path — assess correctness heuristically from preferred case vs adverse events
        adverse = any(
            str(((e.get("trigger") or {}) if isinstance(e.get("trigger"), dict) else {}).get("code") or "")
            in {"bull_case_invalidated", "guidance_withdrawn", "confidence_drop_gt_10"}
            for e in events
        )
        if adverse and dec in {"Approve", "Monitor"}:
            return "Incorrect"
        if adverse:
            return "Partially Correct"
        if dec == "Reject" and adverse:
            return "Correct"
        if lifecycle in {"Closed", "Archived"}:
            return "Inconclusive"
    if review_n:
        return "Process Observation"
    return "Process Observation" if "Process Observation" in OUTCOME_LABELS else "Inconclusive"


def _expected_actual_diff(
    *,
    thesis: dict[str, Any],
    decision: dict[str, Any],
    events: list[dict[str, Any]],
    outcome: str,
    root_cause: str,
) -> tuple[str, str, str]:
    view = str(thesis.get("investment_view") or "Unspecified investment view")
    preferred = str(thesis.get("preferred_case") or "base")
    dec = str(decision.get("decision") or "Wait")
    expected = (
        f"Expected: {preferred} case under thesis '{view[:160]}' with process decision '{dec}'"
    )
    review_actions = [
        str(e.get("recommended_action"))
        for e in events
        if e.get("requires_review") and e.get("recommended_action")
    ]
    if review_actions:
        actual = f"Observed monitoring recommended: {', '.join(sorted(set(review_actions))[:4])}"
    elif outcome == "Incorrect":
        actual = f"Outcome diverged; dominant root-cause bucket: {root_cause}"
    else:
        actual = "No adverse closed-thesis outcome yet — process observation only"
    if outcome in {"Incorrect", "Partially Correct"}:
        difference = (
            f"Difference: thesis weighting appears misaligned with {root_cause.lower()} signals "
            f"relative to expected {preferred} case"
        )
    elif outcome == "Correct":
        difference = "Difference: process decision aligned with subsequent monitoring signals"
    else:
        difference = "Difference: insufficient closed outcome — capture process lesson only"
    return expected, actual, difference


def _lesson_and_guidance(
    *,
    thesis: dict[str, Any],
    root_cause: str,
    category: str,
    outcome: str,
    question: str,
) -> tuple[str, str]:
    view = str(thesis.get("investment_view") or "")
    company = str(thesis.get("company") or "the company")
    text = _blob(question, view)
    if "pricing" in text or "margin" in text or root_cause == "Management":
        lesson = (
            f"The thesis on {company} relied too heavily on operating-margin expansion "
            f"while underweighting pricing pressure ({root_cause})."
        )
        guidance = (
            "Future IT theses should increase weighting for pricing pressure during "
            "weak global discretionary demand."
        )
    elif root_cause == "Macro":
        lesson = (
            f"Macro regime effects were underweighted relative to company-specific {category.lower()} assumptions."
        )
        guidance = (
            "Future theses in this sector should explicitly stress-test discretionary demand and rates paths "
            "before elevating conviction."
        )
    elif root_cause == "Valuation":
        lesson = "Valuation support was treated as durable without enough peer-relative de-rating risk."
        guidance = (
            "Future portfolio ideas should require peer-relative valuation triggers before raising conviction rank."
        )
    elif root_cause == "Timing":
        lesson = "Catalyst timing was optimistic relative to evidence refresh cadence."
        guidance = "Future decisions should tie review dates to hard catalysts (earnings/guidance) rather than open-ended waits."
    elif root_cause == "Hypothesis":
        lesson = "Bull-case fragility was not elevated early enough in committee deliberation."
        guidance = "When bull invalidation signals appear, prefer Committee Review before portfolio rank increases."
    elif outcome == "Process Observation":
        lesson = (
            f"Process observation for {company}: monitoring signals require governance review "
            f"without rewriting the living thesis."
        )
        guidance = (
            f"Preserve process memory under category '{category}' — do not convert monitoring noise into market facts."
        )
    else:
        lesson = (
            f"Investment process lesson ({category}): outcome '{outcome}' traced primarily to {root_cause}."
        )
        guidance = (
            f"Future theses should increase scrutiny on {root_cause.lower()} before advancing decision status."
        )
    return lesson, guidance


def _confidence_change(
    events: list[dict[str, Any]],
    confidence_calibration: dict[str, Any] | None,
) -> dict[str, Any]:
    cc = confidence_calibration or {}
    current = cc.get("overall_confidence")
    if current is None and isinstance(cc.get("report"), dict):
        current = (cc.get("report") or {}).get("overall_confidence")
    prior = None
    delta = None
    for e in events:
        ac = e.get("affected_confidence") if isinstance(e.get("affected_confidence"), dict) else {}
        if ac.get("prior") is not None and ac.get("current") is not None:
            try:
                prior = float(ac["prior"])
                current = float(ac["current"])
                delta = float(ac.get("delta") if ac.get("delta") is not None else current - prior)
                break
            except (TypeError, ValueError):
                continue
    try:
        current_f = float(current) if current is not None else None
    except (TypeError, ValueError):
        current_f = None
    return {"prior": prior, "current": current_f, "delta": delta}


def construct_investment_learning(
    *,
    question: str,
    investment_thesis: dict[str, Any] | None = None,
    decision_office: dict[str, Any] | None = None,
    portfolio_office: dict[str, Any] | None = None,
    monitoring_office: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    thesis = _thesis(investment_thesis)
    decision = _decision(decision_office)
    idea = _idea(portfolio_office)
    events = _events(monitoring_office)
    store = learning_store.get_learning_store()
    timestamp = as_of or _utc_now()

    thesis_id = str(thesis.get("thesis_id") or idea.get("investment_thesis_id") or "") or None
    decision_id = str(decision.get("decision_id") or idea.get("decision_id") or "") or None
    portfolio_id = str(idea.get("idea_id") or (monitoring_office or {}).get("portfolio_idea") or "") or None

    if not thesis_id and not portfolio_id:
        return {
            "ilo_version": ILO_VERSION,
            "schema_version": LEARNING_SCHEMA_VERSION,
            "learning": None,
            "learnings": [],
            "n_learnings": 0,
            "persisted": False,
            "knowledge_factory_updated": False,
            "process_memory": True,
            "mutates_thesis": False,
            "reasoning_changed": False,
            "judgment_changed": False,
            "llm_used": False,
            "fabricated": False,
            "deterministic": True,
            "freeze_locks": dict(FREEZE_LOCKS),
            "note": "No thesis/portfolio context — learning skipped",
            "metadata": dict(metadata or {}),
        }

    root_cause = _root_cause(question=question, thesis=thesis, decision=decision, events=events)
    outcome = _outcome(thesis=thesis, decision=decision, events=events)
    category = _classify_category(
        question=question, thesis=thesis, decision=decision, events=events, root_cause=root_cause
    )
    expected, actual, difference = _expected_actual_diff(
        thesis=thesis, decision=decision, events=events, outcome=outcome, root_cause=root_cause
    )
    lesson, guidance = _lesson_and_guidance(
        thesis=thesis, root_cause=root_cause, category=category, outcome=outcome, question=question
    )
    conf_change = _confidence_change(events, confidence_calibration)
    linked_events = [str(e.get("event_id")) for e in events if e.get("event_id")][:12]
    linked_evidence = []
    for src in (thesis.get("evidence_refs"), decision.get("evidence_refs"), idea.get("dependencies")):
        if isinstance(src, list):
            linked_evidence.extend(str(x) for x in src[:6])
    linked_evidence = linked_evidence[:12]

    learning = {
        "learning_id": _learning_id(thesis_id or "NA", decision_id or "NA", f"{outcome}|{category}|{timestamp}"),
        "thesis_id": thesis_id,
        "decision_id": decision_id,
        "portfolio_id": portfolio_id,
        "outcome": outcome,
        "expected": expected,
        "actual": actual,
        "difference": difference,
        "root_cause": root_cause,
        "lesson": lesson,
        "future_guidance": guidance,
        "confidence_change": conf_change,
        "linked_monitoring_events": linked_events,
        "linked_evidence": linked_evidence,
        "learning_version": "1.0",
        "category": category,
        "company": thesis.get("company") or idea.get("company"),
        "ticker": thesis.get("ticker") or idea.get("ticker"),
        "questions_answered": {
            "what_happened": actual,
            "were_we_correct": outcome,
            "why_if_not": difference if outcome in {"Incorrect", "Partially Correct"} else None,
            "root_cause_bucket": root_cause,
            "what_should_agi_remember": lesson,
        },
        "process_memory": True,
        "knowledge_factory_updated": False,
        "explanation": f"{lesson} Guidance: {guidance}",
        "schema_version": LEARNING_SCHEMA_VERSION,
        "ilo_version": ILO_VERSION,
        "timestamp": timestamp,
        "owner": OWNER,
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "mutates_monitoring": False,
        "metadata": dict(metadata or {}),
    }

    saved = store.upsert(learning) if persist else learning
    pack = {
        "ilo_version": ILO_VERSION,
        "schema_version": LEARNING_SCHEMA_VERSION,
        "learning": saved,
        "learnings": [saved],
        "learning_id": saved.get("learning_id"),
        "n_learnings": 1,
        "category": category,
        "outcome": outcome,
        "persisted": bool(persist),
        "knowledge_factory_updated": False,
        "process_memory": True,
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "mutates_monitoring": False,
        "positions_emitted": False,
        "orders_emitted": False,
        "execution": False,
        "reasoning_changed": False,
        "judgment_changed": False,
        "thesis_changed": False,
        "decision_changed": False,
        "portfolio_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "freeze_locks": dict(FREEZE_LOCKS),
        "as_of": as_of,
        "timestamp": timestamp,
        "metadata": dict(metadata or {}),
        "institutional_guarantee": (
            "ILO stores InvestmentLearning as process memory. "
            "It does not update Knowledge Factory and does not rewrite thesis/decision/portfolio history."
        ),
        "release_note": "Final Office module — AGI v4.0 Investment Office complete after ILO",
    }
    if persist:
        store.record_run(
            {
                "timestamp": timestamp,
                "learning_id": saved.get("learning_id"),
                "thesis_id": thesis_id,
                "outcome": outcome,
                "category": category,
                "knowledge_factory_updated": False,
            }
        )
    return pack
