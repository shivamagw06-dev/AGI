"""IO-01 production façades — observe / inject / Mission Control Observation Center."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Optional

from institutional_observation.classifier import classify_all
from institutional_observation.detector import (
    CompanySnapshot,
    detect_changes,
    snapshot_from_inputs,
)
from institutional_observation.diagnostics import build_diagnostics, validate_observation
from institutional_observation.evaluator import plan_actions, recompute_decision_if_needed
from institutional_observation.flags import flags_dict, is_enabled
from institutional_observation.hysteresis import DEFAULT_HYSTERESIS, HysteresisProfile
from institutional_observation.impact import assess_impact
from institutional_observation.notifier import notify, recent_alerts
from institutional_observation.observation import InstitutionalObservation
from institutional_observation.schema import (
    IO_PRODUCT,
    IO_ROLE,
    IO_SPEC,
    IO_VERSION,
    IO_WORKSTREAM_ID,
    OBSERVATION_ENGINE_VERSION,
)
from institutional_observation.significance import assess_significance

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_SNAPSHOTS: dict[str, CompanySnapshot] = {}
_OBSERVATIONS: dict[str, list[InstitutionalObservation]] = {}
_PENDING_EVENTS: dict[str, list[dict[str, Any]]] = {}


def reset_for_tests() -> None:
    _SNAPSHOTS.clear()
    _OBSERVATIONS.clear()
    _PENDING_EVENTS.clear()
    from institutional_observation.notifier import reset_for_tests as reset_alerts

    reset_alerts()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IO_WORKSTREAM_ID,
        "product": IO_PRODUCT,
        "version": IO_VERSION,
        "role": IO_ROLE,
        "llm": False,
        "proactive": True,
        "hysteresis": DEFAULT_HYSTERESIS.to_dict(),
        "observation_engine_version": OBSERVATION_ENGINE_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": IO_SPEC,
        "brand": "AGI",
        "tickers_tracked": sorted(_SNAPSHOTS.keys()),
        "observation_count": sum(len(v) for v in _OBSERVATIONS.values()),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    """Observation Center soft board for Mission Control."""
    h = health()
    all_obs = [o for rows in _OBSERVATIONS.values() for o in rows]
    today = now_iso()[:10]
    todays = [o for o in all_obs if (o.timestamp or "").startswith(today)]
    critical = [o for o in all_obs if o.severity in {"critical", "high"}]
    decision_changes = [o for o in all_obs if o.decision_changed]
    pending = [o for o in all_obs if o.requires_review]
    return {
        "status": h.get("status"),
        "workstream_id": IO_WORKSTREAM_ID,
        "product": IO_PRODUCT,
        "version": IO_VERSION,
        "llm": False,
        "observation_center": True,
        "todays_observations": len(todays),
        "critical_observations": len(critical),
        "decision_changes": len(decision_changes),
        "pending_reviews": len(pending),
        "observation_latency_ms": None,
        "observation_throughput": len(all_obs),
        "recent_critical": [o.to_dict() for o in critical[-10:]],
        "alerts": recent_alerts(critical_only=True, limit=20),
    }


def _watchlisted(ticker: str) -> bool:
    try:
        from institutional_observation.scheduler import tickers_from_watchlists

        return str(ticker).upper() in set(tickers_from_watchlists())
    except Exception:  # noqa: BLE001
        return False


def _load_current_snapshot(ticker: str) -> tuple[Any, Any, CompanySnapshot, list[str]]:
    from institutional_decision import history as decision_history
    from institutional_decision.production import decide_company
    from institutional_reporting.fixtures import get_fixture

    key = str(ticker or "").strip().upper()
    fixture = get_fixture(key)
    if fixture is None:
        return None, None, CompanySnapshot(ticker=key), [f"no fixture for ticker {key}"]

    latest = decision_history.latest(key)
    if latest is None:
        decide_company({"ticker": key, "include_calibration": True, "include_drift": False})
        latest = decision_history.latest(key)

    snap = snapshot_from_inputs(fixture, latest)
    # Soft FG-01 extras when available
    try:
        from institutional_forecasting.production import get_company_scenarios

        fc = get_company_scenarios(key, include_graph=False, include_propagation=False)
        if fc.get("ok") and fc.get("comparison"):
            # Encode a simple revision signal from bull-bear score spread
            scores = [c.get("confidence") for c in fc["comparison"] if c.get("confidence") is not None]
            snap.extras["forecast_revision"] = (max(scores) - min(scores)) / 100.0 if scores else 0.0
            snap.extras["forecast_scenarios"] = [c.get("scenario") for c in fc["comparison"]]
    except Exception:  # noqa: BLE001
        pass
    return fixture, latest, snap, []


def _graph_meta(ticker: str) -> dict[str, Any]:
    try:
        from institutional_graph.production import _GRAPHS, get_company_graph

        key = str(ticker).upper()
        if key not in _GRAPHS:
            get_company_graph(key, rebuild=True)
        g = _GRAPHS.get(key)
        return dict(g.meta or {}) if g else {}
    except Exception:  # noqa: BLE001
        return {}


def inject_event(ticker: str, event: dict[str, Any]) -> dict[str, Any]:
    """Queue a deterministic institutional event for the next observe cycle."""
    key = str(ticker or "").strip().upper()
    body = dict(event or {})
    body.setdefault("key", body.get("type") or "event")
    _PENDING_EVENTS.setdefault(key, []).append(body)
    return {"ok": True, "ticker": key, "queued": body}


def _observation_id(ticker: str, category: str, severity: str, snap_id: str) -> str:
    raw = f"{ticker}|{category}|{severity}|{snap_id}|{now_iso()}"
    return f"io-{ticker.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _summary_for(classified_top, significance, plan) -> str:
    # Structured factual summary — not LLM prose
    return (
        f"{classified_top.category} | severity={significance.severity} | "
        f"{classified_top.change.detail} | action={plan.recommended_action}"
    )


def observe_company(
    ticker: str,
    *,
    critical_only: bool = False,
    include_decision_changes: bool = True,
    hysteresis: Optional[HysteresisProfile] = None,
    force_events: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Run one observation cycle for a company.

    Compares previous snapshot → current state (+ injected events),
    applies hysteresis, optionally recomputes decision, emits observations.
    """
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": IO_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["IO-01 disabled"],
        }

    t0 = time.perf_counter()
    key = str(ticker or "").strip().upper()
    profile = hysteresis or DEFAULT_HYSTERESIS
    fixture, decision, current, errors = _load_current_snapshot(key)
    if errors:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": IO_WORKSTREAM_ID,
            "validation_errors": errors,
        }

    previous = _SNAPSHOTS.get(key)
    events = list(_PENDING_EVENTS.pop(key, []))
    if force_events:
        events.extend(force_events)

    changes = detect_changes(previous, current, injected_events=events)
    classified = classify_all(changes)
    significance = assess_significance(
        classified, previous=previous, current=current, profile=profile
    )
    watchlist_priority = _watchlisted(key)
    top = classified[0] if classified else None
    plan = plan_actions(
        significance,
        category=top.category if top else "Evidence",
        watchlist_priority=watchlist_priority,
    )

    prev_decision = previous.recommendation if previous else ""
    prev_confidence = previous.confidence if previous else 0
    decision_result = None
    re_evaluated = False
    if plan.recompute_decision:
        decision_result, re_evaluated = recompute_decision_if_needed(key, plan)
        if decision_result and decision_result.get("ok"):
            d = decision_result.get("decision") or {}
            current = CompanySnapshot(
                ticker=current.ticker,
                evidence_ids=current.evidence_ids,
                valuation=current.valuation,
                business_quality=current.business_quality,
                financial_quality=current.financial_quality,
                overall_risk=current.overall_risk,
                recommendation=str(d.get("recommendation") or current.recommendation).upper(),
                confidence=int(d.get("confidence") if d.get("confidence") is not None else current.confidence),
                decision_id=str(d.get("decision_id") or current.decision_id),
                evidence_snapshot_id=str(d.get("evidence_snapshot_id") or current.evidence_snapshot_id),
                company_name=current.company_name,
                sector=current.sector,
                unknowns=current.unknowns,
                risks=current.risks,
                catalysts=current.catalysts,
                extras=current.extras,
            )

    impact = assess_impact(
        classified,
        current=current,
        decision_id=current.decision_id,
        graph_meta=_graph_meta(key),
    )

    report_refreshed = False
    if plan.refresh_report:
        try:
            from institutional_reporting.production import report_for_ticker

            report_for_ticker(key, include_reasons=True)
            report_refreshed = True
        except Exception:  # noqa: BLE001
            report_refreshed = False

    observations: list[InstitutionalObservation] = []
    validation_errors: list[str] = []

    if significance.emit_observation and top is not None:
        snap_id = current.evidence_snapshot_id or hashlib.sha256(
            "|".join(current.evidence_ids).encode()
        ).hexdigest()[:16]
        conf = float(top.confidence)
        if watchlist_priority:
            conf = min(0.99, conf + 0.02)
        obs = InstitutionalObservation(
            observation_id=_observation_id(key, top.category, significance.severity, snap_id),
            company=current.company_name or key,
            ticker=key,
            timestamp=now_iso(),
            category=top.category,
            severity=significance.severity,
            confidence=conf,
            summary=_summary_for(top, significance, plan),
            evidence_snapshot_id=snap_id,
            affected_entities=impact.affected_entities,
            affected_reasons=impact.affected_reasons,
            affected_decisions=impact.affected_decisions,
            affected_forecasts=impact.affected_forecasts,
            requires_review=plan.requires_review,
            recommended_action=plan.recommended_action,
            materiality=significance.materiality,
            decision_changed=bool(prev_decision and prev_decision != current.recommendation),
            previous_decision=prev_decision,
            current_decision=current.recommendation,
            previous_confidence=prev_confidence,
            current_confidence=current.confidence,
            re_evaluated=re_evaluated,
            silent=False,
            watchlist_priority=watchlist_priority,
            diagnostics={
                "changes": [c.to_dict() for c in classified],
                "significance": significance.to_dict(),
                "impact": impact.to_dict(),
                "plan": plan.to_dict(),
                "hysteresis": profile.to_dict(),
                "detected_change_count": len(changes),
            },
            version=IO_VERSION,
            engine_version=OBSERVATION_ENGINE_VERSION,
            hysteresis_version=profile.profile_version,
        )
        errs = validate_observation(obs)
        if errs:
            validation_errors.extend(errs)
        else:
            observations.append(obs)
            notify(obs)
            _OBSERVATIONS.setdefault(key, []).append(obs)
            if len(_OBSERVATIONS[key]) > 200:
                _OBSERVATIONS[key] = _OBSERVATIONS[key][-200:]

    # Persist snapshot after cycle (silent updates still advance baseline)
    _SNAPSHOTS[key] = current

    elapsed = (time.perf_counter() - t0) * 1000.0
    rows = [o.to_dict() for o in observations]
    if critical_only:
        rows = [o for o in rows if o.get("severity") in {"critical", "high"}]
    out: dict[str, Any] = {
        "ok": not validation_errors,
        "rejected": bool(validation_errors),
        "workstream_id": IO_WORKSTREAM_ID,
        "ticker": key,
        "company_name": current.company_name,
        "observations": rows,
        "silent_update": bool(significance.silent_graph_update and not observations),
        "significance": significance.to_dict(),
        "plan": plan.to_dict(),
        "watchlist_priority": watchlist_priority,
        "report_refreshed": report_refreshed,
        "diagnostics": build_diagnostics(observations, ticker=key, latency_ms=elapsed),
        "validation_errors": validation_errors,
        "llm": False,
    }
    if include_decision_changes:
        out["decision_changes"] = [
            {
                "previous": prev_decision,
                "current": current.recommendation,
                "changed": bool(prev_decision and prev_decision != current.recommendation),
                "previous_confidence": prev_confidence,
                "current_confidence": current.confidence,
                "re_evaluated": re_evaluated,
            }
        ]
        if decision_result is not None:
            out["decision_result"] = {
                "ok": decision_result.get("ok"),
                "recommendation": (decision_result.get("decision") or {}).get("recommendation"),
                "confidence": (decision_result.get("decision") or {}).get("confidence"),
            }
    return out


def get_company_observations(
    ticker: str,
    *,
    critical_only: bool = False,
    include_decision_changes: bool = True,
    observe: Optional[bool] = None,
) -> dict[str, Any]:
    key = str(ticker or "").strip().upper()
    should_observe = key not in _SNAPSHOTS if observe is None else bool(observe)
    if should_observe:
        # Establish baseline on first access; subsequent identical ticks stay silent.
        result = observe_company(
            key,
            critical_only=critical_only,
            include_decision_changes=include_decision_changes,
        )
        # Prefer accumulated history for the company workspace timeline.
        rows = [o.to_dict() for o in _OBSERVATIONS.get(key, [])]
        if critical_only:
            rows = [r for r in rows if r.get("severity") in {"critical", "high"}]
        result = dict(result)
        result["observations"] = rows
        return result
    rows = [o.to_dict() for o in _OBSERVATIONS.get(key, [])]
    if critical_only:
        rows = [r for r in rows if r.get("severity") in {"critical", "high"}]
    out: dict[str, Any] = {
        "ok": True,
        "workstream_id": IO_WORKSTREAM_ID,
        "ticker": key,
        "observations": rows,
        "cached": True,
        "llm": False,
    }
    if include_decision_changes and rows:
        latest = rows[-1]
        out["decision_changes"] = [
            {
                "previous": latest.get("previous_decision"),
                "current": latest.get("current_decision"),
                "changed": bool(latest.get("decision_changed")),
                "previous_confidence": latest.get("previous_confidence"),
                "current_confidence": latest.get("current_confidence"),
                "re_evaluated": bool(latest.get("re_evaluated")),
            }
        ]
    return out


def _normalize_events(events: Any) -> Optional[list[dict[str, Any]]]:
    if not events:
        return None
    if isinstance(events, str):
        key = events.strip().lower()
        return [{"key": key, "detail": f"Injected institutional event: {key}", "magnitude": 1.0}]
    if isinstance(events, dict):
        body = dict(events)
        body.setdefault("key", body.get("type") or "event")
        return [body]
    out: list[dict[str, Any]] = []
    for item in events:
        if isinstance(item, str):
            key = item.strip().lower()
            out.append(
                {"key": key, "detail": f"Injected institutional event: {key}", "magnitude": 1.0}
            )
        elif isinstance(item, dict):
            body = dict(item)
            body.setdefault("key", body.get("type") or "event")
            out.append(body)
    return out or None


def observation_company(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    ticker = str(body.get("ticker") or "").strip()
    critical_only = body.get("critical_only", False)
    include_decision_changes = body.get("include_decision_changes", True)
    if isinstance(critical_only, str):
        critical_only = critical_only.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_decision_changes, str):
        include_decision_changes = include_decision_changes.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    events = _normalize_events(body.get("events") or body.get("inject") or body.get("force_events"))
    # Baseline then observe when injecting so hysteresis compares against prior state.
    if events:
        observe_company(ticker)
    return observe_company(
        ticker,
        critical_only=bool(critical_only),
        include_decision_changes=bool(include_decision_changes),
        force_events=events,
    )
