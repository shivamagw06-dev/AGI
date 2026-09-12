"""RW-01 timeline — chronological reconstruction of investment evolution."""

from __future__ import annotations

import hashlib
from typing import Any, Sequence

from institutional_workspace.models import TimelineEvent

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _eid(kind: str, key: str) -> str:
    return f"tl-{kind}-{hashlib.sha256(f'{kind}|{key}'.encode()).hexdigest()[:10]}"


def build_timeline(
    *,
    context: str,
    subject_id: str,
    company_decision: dict[str, Any] | None = None,
    portfolio_risk: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    portfolio_decision: dict[str, Any] | None = None,
    committee: dict[str, Any] | None = None,
    observations: Sequence[dict[str, Any]] = (),
    forecasts: Sequence[dict[str, Any]] = (),
    evidence: Sequence[dict[str, Any]] = (),
) -> tuple[TimelineEvent, ...]:
    events: list[TimelineEvent] = []
    ts = now_iso()

    for ev in evidence:
        events.append(
            TimelineEvent(
                event_id=_eid("evidence", str(ev.get("evidence_id") or ev.get("title"))),
                timestamp=str(ev.get("date") or ts),
                kind="evidence",
                title=str(ev.get("title") or "Evidence filed"),
                object_type="Evidence",
                object_id=str(ev.get("evidence_id") or ""),
                summary=str(ev.get("snippet") or ev.get("source_type") or ""),
                severity="info",
            )
        )

    for obs in observations:
        events.append(
            TimelineEvent(
                event_id=_eid("observation", str(obs.get("id") or obs.get("title") or "obs")),
                timestamp=str(obs.get("generated_at") or obs.get("timestamp") or ts),
                kind="observation",
                title=str(obs.get("title") or obs.get("kind") or "Observation"),
                object_type="Observation",
                object_id=str(obs.get("id") or ""),
                summary=str(obs.get("detail") or obs.get("summary") or ""),
                severity=str(obs.get("severity") or "medium"),
            )
        )

    if company_decision:
        events.append(
            TimelineEvent(
                event_id=_eid("decision", str(company_decision.get("decision_id") or subject_id)),
                timestamp=str(company_decision.get("generated_at") or ts),
                kind="decision_updated",
                title=f"Decision updated: {company_decision.get('recommendation') or '—'}",
                object_type="CompanyDecision",
                object_id=str(company_decision.get("decision_id") or subject_id),
                summary=str(company_decision.get("rule_path") or company_decision.get("note") or ""),
                severity="medium",
            )
        )

    for fc in forecasts:
        events.append(
            TimelineEvent(
                event_id=_eid("forecast", str(fc.get("id") or "forecast")),
                timestamp=str(fc.get("generated_at") or ts),
                kind="forecast",
                title=str(fc.get("title") or "Forecast refreshed"),
                object_type="Forecast",
                object_id=str(fc.get("id") or ""),
                summary=str(fc.get("summary") or ""),
                severity="info",
            )
        )

    if portfolio_risk:
        events.append(
            TimelineEvent(
                event_id=_eid("risk", str(portfolio_risk.get("risk_id") or subject_id)),
                timestamp=str(portfolio_risk.get("generated_at") or ts),
                kind="risk_changed",
                title=f"Risk changed: {portfolio_risk.get('overall_risk') or '—'}",
                object_type="PortfolioRisk",
                object_id=str(portfolio_risk.get("risk_id") or ""),
                summary=f"Concentration {(portfolio_risk.get('concentration') or {}).get('level')}",
                severity="high" if portfolio_risk.get("overall_risk") in {"High", "Critical"} else "medium",
            )
        )

    if policy:
        status = policy.get("overall_status") or ""
        events.append(
            TimelineEvent(
                event_id=_eid("policy", str(policy.get("policy_id") or subject_id)),
                timestamp=str(policy.get("generated_at") or ts),
                kind="policy_breach" if "Breach" in status else "policy",
                title=f"Policy: {status}",
                object_type="PolicyAssessment",
                object_id=str(policy.get("policy_id") or ""),
                summary=f"Violations={policy.get('violation_count') or len(policy.get('violations') or [])}",
                severity="critical" if "Critical" in status else ("high" if "Breach" in status else "info"),
            )
        )

    if portfolio_decision:
        events.append(
            TimelineEvent(
                event_id=_eid("cio", str(portfolio_decision.get("decision_id") or subject_id)),
                timestamp=str(portfolio_decision.get("generated_at") or ts),
                kind="portfolio_decision",
                title=f"Portfolio decision: {portfolio_decision.get('recommendation') or '—'}",
                object_type="PortfolioDecision",
                object_id=str(portfolio_decision.get("decision_id") or ""),
                summary=str(portfolio_decision.get("rule_path") or ""),
                severity="medium",
            )
        )

    if committee:
        events.append(
            TimelineEvent(
                event_id=_eid("committee", str(committee.get("resolution_id") or subject_id)),
                timestamp=str(committee.get("generated_at") or ts),
                kind="committee",
                title=f"Committee: {committee.get('status') or '—'}",
                object_type="CommitteeResolution",
                object_id=str(committee.get("resolution_id") or ""),
                summary=str(committee.get("outcome") or ""),
                severity="high",
            )
        )

    # Deterministic sort: severity weight then title for stable ordering when timestamps equal
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    events.sort(key=lambda e: (e.timestamp, severity_rank.get(e.severity, 9), e.title))
    return tuple(events)
