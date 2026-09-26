"""IDS-01 production façades — health / decide / history (IDS-02 calibration wired)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_decision.decision_engine import generate_decision
from institutional_decision.decision_validator import validate_decision
from institutional_decision.diagnostics import build_diagnostics
from institutional_decision.flags import flags_dict, is_enabled
from institutional_decision import history as decision_history
from institutional_decision.schema import (
    DECISION_ENGINE_VERSION,
    DECISION_VALIDATOR_VERSION,
    IDS_PRODUCT,
    IDS_ROLE,
    IDS_SPEC,
    IDS_VERSION,
    IDS_WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IDS_WORKSTREAM_ID,
        "product": IDS_PRODUCT,
        "version": IDS_VERSION,
        "role": IDS_ROLE,
        "owns_recommendation": True,
        "llm": False,
        "external_writer": False,
        "decision_engine_version": DECISION_ENGINE_VERSION,
        "validator_version": DECISION_VALIDATOR_VERSION,
        "calibration": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": IDS_SPEC,
        "brand": "AGI",
        "history": decision_history.metrics(),
        "as_of": now_iso(),
    }


def _apply_calibration(
    decision: Any,
    *,
    reasons: Any,
    evidence: Any,
    previous: Any,
) -> tuple[Any, dict[str, Any] | None, list[str]]:
    """IDS-02 — compute confidence; attach calibration bundle."""
    try:
        from institutional_calibration.calibration_engine import (
            calibrate_decision,
            calibration_summary,
        )
        from institutional_calibration.flags import is_enabled as cal_enabled
        from institutional_calibration.diagnostics import validate_calibration_gates
    except Exception as exc:  # noqa: BLE001
        return decision, None, [f"calibration unavailable: {exc}"]

    if not cal_enabled():
        return decision, None, ["IDS-02 disabled"]

    updated, bundle = calibrate_decision(
        decision, reasons=reasons, evidence=evidence, previous=previous
    )
    errors = validate_calibration_gates(bundle.quality_gates)
    return updated, calibration_summary(bundle), errors


def _decide_from_report_input(
    inp: Any,
    *,
    reason_graph: Any = None,
    include_calibration: bool = True,
    include_drift: bool = True,
) -> dict[str, Any]:
    from institutional_reporting.schema import IRE_VERSION, REASON_COMPOSER_VERSION

    prev = decision_history.latest(inp.ticker)
    previous_version = prev.decision_version if prev else 0
    reasons = None
    if reason_graph is not None and hasattr(reason_graph, "reasons"):
        reasons = reason_graph.reasons
    evidence_ids = [e.evidence_id for e in (inp.evidence or ()) if getattr(e, "evidence_id", None)]
    decision = generate_decision(
        reasons=reasons,
        valuation=inp.valuation,
        risks=list(inp.risks or ()),
        confidence=inp.confidence,
        business_quality=inp.business_quality,
        financial_quality=inp.financial_quality,
        overall_risk=inp.overall_risk,
        ticker=inp.ticker,
        company_name=inp.company_name,
        sector=inp.sector,
        unknowns=list(inp.unknowns or ()),
        evidence_ids=evidence_ids,
        reason_version=REASON_COMPOSER_VERSION,
        report_version=IRE_VERSION,
        previous_version=previous_version,
        investment_horizon=str(inp.horizon or ""),
    )
    validation = validate_decision(
        decision,
        business_quality=inp.business_quality,
        valuation=str(inp.valuation or ""),
        overall_risk=str(inp.overall_risk or ""),
    )
    if not validation.ok:
        diagnostics = build_diagnostics(decision, validation)
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": IDS_WORKSTREAM_ID,
            "validation_errors": validation.errors,
            "decision": decision.to_dict(),
            "diagnostics": diagnostics,
        }

    calibrated, cal_summary, cal_errors = _apply_calibration(
        decision, reasons=reasons, evidence=inp, previous=prev
    )
    if cal_errors:
        diagnostics = build_diagnostics(calibrated, validation)
        diagnostics["calibration_errors"] = cal_errors
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": IDS_WORKSTREAM_ID,
            "validation_errors": cal_errors,
            "decision": calibrated.to_dict(),
            "diagnostics": diagnostics,
            "calibration": cal_summary if include_calibration else None,
        }

    # KG-01 — bind decision to DecisionNode in company knowledge graph
    try:
        from dataclasses import replace as dc_replace

        from institutional_graph.flags import is_enabled as kg_enabled
        from institutional_graph.graph import build_company_graph
        from institutional_graph.impact import compute_impacts
        from institutional_graph.inference import infer
        from institutional_graph.production import _GRAPHS

        if kg_enabled():
            kg = build_company_graph(inp, reasons=reasons, decision=calibrated)
            infer(kg)
            compute_impacts(kg, inp)
            calibrated = dc_replace(
                calibrated,
                knowledge_graph_id=kg.graph_id,
                decision_node_id=kg.decision_node_id,
            )
            _GRAPHS[str(inp.ticker or "").strip().upper()] = kg
    except Exception:  # noqa: BLE001
        pass

    decision_history.record(calibrated)
    diagnostics = build_diagnostics(calibrated, validation)
    if cal_summary:
        diagnostics["calibration_version"] = calibrated.calibration_version
        diagnostics["calibration_profile_version"] = calibrated.calibration_profile_version
        diagnostics["calibrated"] = True
        if include_drift and cal_summary.get("drift"):
            diagnostics["decision_drift"] = cal_summary["drift"]
    if getattr(calibrated, "knowledge_graph_id", ""):
        diagnostics["knowledge_graph_id"] = calibrated.knowledge_graph_id
        diagnostics["decision_node_id"] = calibrated.decision_node_id

    out: dict[str, Any] = {
        "ok": True,
        "rejected": False,
        "workstream_id": IDS_WORKSTREAM_ID,
        "decision": calibrated.to_dict(),
        "diagnostics": diagnostics,
        "institutional_decision": calibrated,
    }
    if include_calibration and cal_summary:
        out["calibration"] = cal_summary.get("breakdown")
        out["scorecard"] = cal_summary.get("scorecard")
        out["explainability"] = cal_summary.get("explainability")
        out["lineage"] = cal_summary.get("lineage")
        out["calibration_quality_gates"] = cal_summary.get("quality_gates")
        out["calibration_diagnostics"] = cal_summary.get("diagnostics")
    if include_drift and cal_summary:
        out["drift"] = cal_summary.get("drift")
    return out


def decide_company(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """POST /v1/decision/company"""
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": IDS_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["IDS-01 disabled"],
        }
    body = dict(payload or {})
    include_history = body.pop("include_history", False)
    include_calibration = body.pop("include_calibration", True)
    include_drift = body.pop("include_drift", True)
    if isinstance(include_history, str):
        include_history = include_history.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_calibration, str):
        include_calibration = include_calibration.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_drift, str):
        include_drift = include_drift.strip().lower() in {"1", "true", "yes", "on"}

    from institutional_reporting.fixtures import get_fixture
    from institutional_reporting.models import InstitutionalReportInput
    from institutional_reporting.reason_composer import compose_reasons

    ticker = str(body.get("ticker") or "").strip()
    occupied = {k for k, v in body.items() if v not in (None, "", [], {})}
    ticker_only = occupied <= {
        "ticker",
        "as_of",
        "include_history",
        "include_calibration",
        "include_drift",
    } and bool(ticker)

    if ticker_only and get_fixture(ticker):
        inp = get_fixture(ticker)
    else:
        inp = InstitutionalReportInput.from_dict(body)

    graph = compose_reasons(inp)
    result = _decide_from_report_input(
        inp,
        reason_graph=graph,
        include_calibration=include_calibration,
        include_drift=include_drift,
    )
    result.pop("institutional_decision", None)
    if include_history and inp.ticker:
        result["history"] = decision_history.history_for(inp.ticker)
    return result


def get_company_decision(
    ticker: str,
    *,
    include_history: bool = False,
    include_calibration: bool = True,
    include_drift: bool = True,
) -> dict[str, Any]:
    """GET /v1/decision/company/{ticker} — latest or freshly generated from fixture."""
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": IDS_WORKSTREAM_ID}
    latest = decision_history.latest(ticker)
    if latest is None or not getattr(latest, "calibrated", False):
        generated = decide_company(
            {
                "ticker": ticker,
                "include_history": include_history,
                "include_calibration": include_calibration,
                "include_drift": include_drift,
            }
        )
        return generated

    validation = validate_decision(latest)
    out: dict[str, Any] = {
        "ok": validation.ok,
        "rejected": not validation.ok,
        "workstream_id": IDS_WORKSTREAM_ID,
        "decision": latest.to_dict(),
        "diagnostics": build_diagnostics(latest, validation),
        "validation_errors": validation.errors,
    }
    if include_calibration:
        try:
            from institutional_calibration.calibration_engine import (
                calibrate_decision,
                calibration_summary,
            )
            from institutional_calibration.confidence import confidence_breakdown_dict
            from institutional_decision.models import InstitutionalDecision
            from institutional_reporting.fixtures import get_fixture
            from institutional_reporting.reason_composer import compose_reasons

            fixture = get_fixture(ticker)
            if fixture is not None:
                graph = compose_reasons(fixture)
                prev_list = decision_history.history_for(ticker)
                previous = None
                if len(prev_list) >= 2:
                    previous = InstitutionalDecision.from_dict(prev_list[-2]["decision"])
                # Rebuild explainability/scorecard/drift; keep stored confidence on decision
                _, bundle = calibrate_decision(
                    latest, reasons=graph.reasons, evidence=fixture, previous=previous
                )
                summary = calibration_summary(bundle)
                if hasattr(latest.calibration, "final_confidence"):
                    out["calibration"] = confidence_breakdown_dict(latest.calibration)
                elif isinstance(latest.calibration, dict):
                    out["calibration"] = latest.calibration
                else:
                    out["calibration"] = summary.get("breakdown")
                out["scorecard"] = summary.get("scorecard")
                out["explainability"] = summary.get("explainability")
                out["lineage"] = summary.get("lineage")
                if include_drift:
                    out["drift"] = summary.get("drift")
        except Exception:  # noqa: BLE001
            if latest.calibration is not None:
                out["calibration"] = (
                    latest.calibration.to_dict()
                    if hasattr(latest.calibration, "to_dict")
                    else latest.calibration
                )
    if include_history:
        out["history"] = decision_history.history_for(ticker)
    return out


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    return {
        "status": h.get("status"),
        "workstream_id": IDS_WORKSTREAM_ID,
        "product": IDS_PRODUCT,
        "version": IDS_VERSION,
        "owns_recommendation": True,
        "llm": False,
        "calibration": True,
        "history": h.get("history"),
    }
