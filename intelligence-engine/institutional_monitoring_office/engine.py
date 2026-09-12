"""Deterministic Institutional Monitoring Office.

Emits MonitoringEvents that recommend review — never mutates thesis, decision, or portfolio.
Answers “What changed?” not merely “What happened?”
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from institutional_monitoring_office import store as event_store
from institutional_monitoring_office.schema import (
    CONFIDENCE_DROP_REVIEW_THRESHOLD,
    EVENT_SCHEMA_VERSION,
    FREEZE_LOCKS,
    IMO_VERSION,
    MONITOR_DOMAINS,
    OWNER,
    RECOMMENDED_ACTIONS,
    SEVERITIES,
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


def _confidence_value(
    *,
    thesis: dict[str, Any],
    decision: dict[str, Any],
    confidence_calibration: dict[str, Any] | None,
) -> float:
    cc = confidence_calibration or {}
    for candidate in (
        cc.get("overall_confidence"),
        (cc.get("report") or {}).get("overall_confidence") if isinstance(cc.get("report"), dict) else None,
        thesis.get("confidence"),
        decision.get("confidence"),
    ):
        if candidate is None:
            continue
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return 50.0


def _event_id(idea_id: str, code: str, nonce: str) -> str:
    raw = f"{idea_id}|{code}|{nonce}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"ME-{digest}"


def _make_event(
    *,
    idea_id: str,
    code: str,
    domain: str,
    source: str,
    severity: str,
    thesis_id: str | None,
    decision_id: str | None,
    affected_confidence: dict[str, Any] | None,
    recommended_action: str,
    requires_review: bool,
    explanation: str,
    timestamp: str,
    nonce: str,
) -> dict[str, Any]:
    sev = severity if severity in SEVERITIES else "medium"
    action = recommended_action if recommended_action in RECOMMENDED_ACTIONS else "Review"
    return {
        "event_id": _event_id(idea_id, code, nonce),
        "portfolio_idea": idea_id,
        "trigger": {
            "code": code,
            "domain": domain if domain in MONITOR_DOMAINS else "Sector",
            "description": explanation,
        },
        "source": source,
        "severity": sev,
        "affected_thesis": thesis_id,
        "affected_decision": decision_id,
        "affected_confidence": affected_confidence,
        "recommended_action": action,
        "requires_review": bool(requires_review),
        "timestamp": timestamp,
        "explanation": explanation,
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "schema_version": EVENT_SCHEMA_VERSION,
        "imo_version": IMO_VERSION,
        "owner": OWNER,
    }


def _blob(*parts: Any) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def _detect_triggers(
    *,
    question: str,
    idea: dict[str, Any],
    thesis: dict[str, Any],
    decision: dict[str, Any],
    confidence_calibration: dict[str, Any] | None,
    hypothesis_evaluation: dict[str, Any] | None,
    committee_reasoning: dict[str, Any] | None,
    store: event_store.MonitoringEventStore,
    timestamp: str,
) -> list[dict[str, Any]]:
    idea_id = str(idea.get("idea_id") or "PI-UNKNOWN")
    thesis_id = str(thesis.get("thesis_id") or idea.get("investment_thesis_id") or "") or None
    decision_id = str(decision.get("decision_id") or idea.get("decision_id") or "") or None
    conf = _confidence_value(
        thesis=thesis, decision=decision, confidence_calibration=confidence_calibration
    )
    prior = store.get_prior_confidence(idea_id)
    events: list[dict[str, Any]] = []
    text = _blob(
        question,
        thesis.get("investment_view"),
        thesis.get("monitoring_checklist"),
        idea.get("monitoring"),
        (committee_reasoning or {}).get("summary"),
        (hypothesis_evaluation or {}).get("summary"),
    )

    # 1) Confidence dropped >10 → Review
    if prior is not None and (prior - conf) > CONFIDENCE_DROP_REVIEW_THRESHOLD:
        drop = round(prior - conf, 2)
        events.append(
            _make_event(
                idea_id=idea_id,
                code="confidence_drop_gt_10",
                domain="Confidence",
                source="confidence_calibration",
                severity="high" if drop >= 20 else "medium",
                thesis_id=thesis_id,
                decision_id=decision_id,
                affected_confidence={
                    "prior": prior,
                    "current": conf,
                    "delta": -drop,
                    "threshold": CONFIDENCE_DROP_REVIEW_THRESHOLD,
                },
                recommended_action="Review",
                requires_review=True,
                explanation=f"Confidence dropped {drop} points (>{CONFIDENCE_DROP_REVIEW_THRESHOLD}) — recommend review",
                timestamp=timestamp,
                nonce=f"conf-{prior}-{conf}",
            )
        )

    # 2) Bull case invalidated → Committee Review
    he = hypothesis_evaluation or {}
    icr = committee_reasoning or {}
    bull_invalid = False
    for blob in (
        he.get("invalidated") or [],
        he.get("invalidated_hypotheses") or [],
        (he.get("evaluation") or {}).get("invalidated") if isinstance(he.get("evaluation"), dict) else [],
        icr.get("invalidated_cases") or [],
    ):
        if isinstance(blob, list) and any("bull" in str(x).lower() for x in blob):
            bull_invalid = True
        if isinstance(blob, str) and "bull" in blob.lower() and "invalid" in blob.lower():
            bull_invalid = True
    if "bull case invalid" in text or "bull invalidated" in text or bull_invalid:
        events.append(
            _make_event(
                idea_id=idea_id,
                code="bull_case_invalidated",
                domain="Management Commentary",
                source="committee_reasoning",
                severity="critical",
                thesis_id=thesis_id,
                decision_id=decision_id,
                affected_confidence={"current": conf, "note": "bull_case_invalidated"},
                recommended_action="Committee Review",
                requires_review=True,
                explanation="Bull case invalidated — escalate to committee review",
                timestamp=timestamp,
                nonce="bull-invalid",
            )
        )

    # 3) Management guidance withdrawn → Escalate
    if any(
        x in text
        for x in (
            "guidance withdrawn",
            "withdraw guidance",
            "withdrew guidance",
            "suspend guidance",
            "guidance suspended",
            "no guidance",
        )
    ):
        events.append(
            _make_event(
                idea_id=idea_id,
                code="guidance_withdrawn",
                domain="Guidance",
                source="management_commentary",
                severity="critical",
                thesis_id=thesis_id,
                decision_id=decision_id,
                affected_confidence={"current": conf, "note": "guidance_withdrawn"},
                recommended_action="Escalate",
                requires_review=True,
                explanation="Management guidance withdrawn — escalate governance review",
                timestamp=timestamp,
                nonce="guidance-withdrawn",
            )
        )

    # 4) Quarterly results published → Refresh Thesis
    if any(
        x in text
        for x in (
            "quarterly results",
            "q1 results",
            "q2 results",
            "q3 results",
            "q4 results",
            "earnings released",
            "results published",
            "reported earnings",
            "results out",
        )
    ):
        events.append(
            _make_event(
                idea_id=idea_id,
                code="quarterly_results_published",
                domain="Earnings",
                source="earnings_calendar",
                severity="medium",
                thesis_id=thesis_id,
                decision_id=decision_id,
                affected_confidence={"current": conf, "note": "results_published"},
                recommended_action="Refresh Thesis",
                requires_review=True,
                explanation="Quarterly results published — refresh investment thesis",
                timestamp=timestamp,
                nonce="results-published",
            )
        )

    # Domain-aware situational triggers from monitoring checklist / question
    domain_rules: list[tuple[tuple[str, ...], str, str, str, str]] = [
        (("competitor", "peer win", "peer lose", "rival"), "Competitor", "competitor_event", "low", "Monitor"),
        (("valuation", "multiple expansion", "de-rate", "rerating"), "Valuation", "valuation_shift", "medium", "Review"),
        (("sector", "industry", "it services demand"), "Sector", "sector_development", "low", "Monitor"),
        (("regulatory", "sebi", "rbi", "policy change"), "Regulatory", "regulatory_change", "medium", "Review"),
        (("macro", "rates", "fx", "inflation", "gdp"), "Macro", "macro_indicator", "low", "Monitor"),
        (("dividend", "buyback", "split", "demerger", "acquisition"), "Corporate Actions", "corporate_action", "medium", "Review"),
        (("management commentary", "ceo said", "cfo said", "conference call"), "Management Commentary", "management_commentary", "info", "Monitor"),
    ]
    for keywords, domain, code, sev, action in domain_rules:
        if any(k in text for k in keywords):
            # Avoid duplicating already-emitted high-priority codes
            if any(e.get("trigger", {}).get("code") == code for e in events):
                continue
            events.append(
                _make_event(
                    idea_id=idea_id,
                    code=code,
                    domain=domain,
                    source="portfolio_idea_monitoring",
                    severity=sev,
                    thesis_id=thesis_id,
                    decision_id=decision_id,
                    affected_confidence={"current": conf},
                    recommended_action=action,
                    requires_review=action in {"Review", "Committee Review", "Escalate", "Refresh Thesis"},
                    explanation=f"{domain} signal detected — recommended action: {action}",
                    timestamp=timestamp,
                    nonce=f"{code}-{domain}",
                )
            )

    # Coverage heartbeat — ensures continuous domain watch without mutating objects
    covered = list(MONITOR_DOMAINS)
    events.append(
        _make_event(
            idea_id=idea_id,
            code="coverage_heartbeat",
            domain="Sector",
            source="institutional_monitoring_office",
            severity="info",
            thesis_id=thesis_id,
            decision_id=decision_id,
            affected_confidence={"current": conf, "prior": prior},
            recommended_action="Monitor",
            requires_review=False,
            explanation=(
                f"Continuous monitoring coverage across {len(covered)} domains — "
                "events recommend review; thesis/decision/portfolio unchanged"
            ),
            timestamp=timestamp,
            nonce=f"heartbeat-{timestamp}",
        )
    )
    events[-1]["domains_covered"] = covered

    # Persist latest confidence for next delta detection (does not mutate thesis)
    store.set_prior_confidence(idea_id, conf)
    return events


def run_monitoring_office(
    *,
    question: str,
    portfolio_office: dict[str, Any] | None = None,
    investment_thesis: dict[str, Any] | None = None,
    decision_office: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    idea = _idea(portfolio_office)
    thesis = _thesis(investment_thesis)
    decision = _decision(decision_office)
    store = event_store.get_monitoring_store()
    timestamp = as_of or _utc_now()

    if not idea.get("idea_id"):
        # Soft degrade — still emit empty pack without inventing portfolio ideas
        return {
            "imo_version": IMO_VERSION,
            "schema_version": EVENT_SCHEMA_VERSION,
            "events": [],
            "event_ids": [],
            "n_events": 0,
            "requires_review": 0,
            "domains_covered": list(MONITOR_DOMAINS),
            "persisted": False,
            "mutates_thesis": False,
            "mutates_decision": False,
            "mutates_portfolio": False,
            "positions_emitted": False,
            "orders_emitted": False,
            "reasoning_changed": False,
            "judgment_changed": False,
            "thesis_changed": False,
            "decision_changed": False,
            "portfolio_changed": False,
            "llm_used": False,
            "fabricated": False,
            "deterministic": True,
            "freeze_locks": dict(FREEZE_LOCKS),
            "note": "No portfolio idea — monitoring skipped",
            "metadata": dict(metadata or {}),
        }

    raw_events = _detect_triggers(
        question=question,
        idea=idea,
        thesis=thesis,
        decision=decision,
        confidence_calibration=confidence_calibration,
        hypothesis_evaluation=hypothesis_evaluation,
        committee_reasoning=committee_reasoning,
        store=store,
        timestamp=timestamp,
    )

    saved: list[dict[str, Any]] = []
    if persist:
        for ev in raw_events:
            saved.append(store.upsert(ev))
    else:
        saved = raw_events

    review_events = [e for e in saved if e.get("requires_review")]
    pack = {
        "imo_version": IMO_VERSION,
        "schema_version": EVENT_SCHEMA_VERSION,
        "portfolio_idea": idea.get("idea_id"),
        "company": idea.get("company") or thesis.get("company"),
        "ticker": idea.get("ticker") or thesis.get("ticker"),
        "events": saved,
        "event_ids": [e.get("event_id") for e in saved],
        "n_events": len(saved),
        "requires_review": len(review_events),
        "review_queue": [
            {
                "event_id": e.get("event_id"),
                "recommended_action": e.get("recommended_action"),
                "severity": e.get("severity"),
                "trigger": e.get("trigger"),
            }
            for e in review_events
        ],
        "domains_covered": list(MONITOR_DOMAINS),
        "affected_thesis": thesis.get("thesis_id") or idea.get("investment_thesis_id"),
        "affected_decision": decision.get("decision_id") or idea.get("decision_id"),
        "persisted": bool(persist),
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
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
            "IMO emits MonitoringEvents that recommend review. "
            "It never modifies Investment Thesis, Decision, or Portfolio Idea objects."
        ),
    }
    if persist:
        store.record_run(
            {
                "timestamp": timestamp,
                "portfolio_idea": pack["portfolio_idea"],
                "n_events": pack["n_events"],
                "requires_review": pack["requires_review"],
                "event_ids": pack["event_ids"],
            }
        )
    return pack
