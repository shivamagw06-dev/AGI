"""Report composer — Facts → Reasons → Decision System → Report (IDS-01)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any, Union

from institutional_reporting.flags import is_enabled
from institutional_reporting.models import InstitutionalReport, InstitutionalReportInput
from institutional_reporting.reason_composer import compose_reasons
from institutional_reporting.renderer import (
    render_reason_graph_text,
    render_sections_from_reasons,
    render_text,
)
from institutional_reporting.schema import (
    IRE_REPORT_TYPE,
    IRE_VERSION,
    IRE_WORKSTREAM_ID,
    REASON_COMPOSER_VERSION,
    REPORT_SECTIONS,
    VALIDATOR_VERSION,
)
from institutional_reporting.validator import validate_input, validate_reasons

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _fingerprint(inp: InstitutionalReportInput) -> str:
    payload = json.dumps(inp.to_dict(), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_diagnostics(
    inp: InstitutionalReportInput,
    *,
    reason_count: int,
    gates: dict[str, bool],
    decision: Any = None,
) -> dict[str, Any]:
    evidence_count = len(inp.evidence or ())
    gate_pass = bool(gates) and all(gates.values())
    out = {
        "generated_at": now_iso(),
        "report_version": IRE_REPORT_TYPE,
        "ire_version": IRE_VERSION,
        "reason_composer_version": REASON_COMPOSER_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "reason_object_count": reason_count,
        "evidence_count": evidence_count,
        "quality_gate": "PASS" if gate_pass else "FAIL",
        "quality_gate_pass": gate_pass,
        "llm": False,
        "external_writer": False,
        "section_count": len(REPORT_SECTIONS),
        "decision_system": True,
    }
    if decision is not None:
        out["decision_id"] = getattr(decision, "decision_id", None) or (
            decision.get("decision_id") if isinstance(decision, dict) else None
        )
        out["decision_version"] = getattr(decision, "decision_version", None) or (
            decision.get("decision_version") if isinstance(decision, dict) else None
        )
        out["evidence_snapshot_id"] = getattr(decision, "evidence_snapshot_id", None) or (
            decision.get("evidence_snapshot_id") if isinstance(decision, dict) else None
        )
        out["calibrated"] = bool(
            getattr(decision, "calibrated", False)
            if not isinstance(decision, dict)
            else decision.get("calibrated")
        )
        out["calibration_version"] = getattr(decision, "calibration_version", None) or (
            decision.get("calibration_version") if isinstance(decision, dict) else None
        )
        out["calibration_profile_version"] = getattr(
            decision, "calibration_profile_version", None
        ) or (
            decision.get("calibration_profile_version") if isinstance(decision, dict) else None
        )
        cal = getattr(decision, "calibration", None)
        if cal is None and isinstance(decision, dict):
            cal = decision.get("calibration")
        if cal is not None:
            out["confidence_contributors"] = (
                {
                    "positive": [c.to_dict() for c in getattr(cal, "positive_contributors", [])],
                    "negative": [c.to_dict() for c in getattr(cal, "negative_contributors", [])],
                }
                if hasattr(cal, "positive_contributors")
                else {
                    "positive": (cal.get("positive_contributors") if isinstance(cal, dict) else []),
                    "negative": (cal.get("negative_contributors") if isinstance(cal, dict) else []),
                }
            )
            out["penalty_breakdown"] = (
                {
                    "unknown_penalty": getattr(cal, "unknown_penalty", None),
                    "contradiction_penalty": getattr(cal, "contradiction_penalty", None),
                }
                if hasattr(cal, "unknown_penalty")
                else {
                    "unknown_penalty": cal.get("unknown_penalty") if isinstance(cal, dict) else None,
                    "contradiction_penalty": cal.get("contradiction_penalty")
                    if isinstance(cal, dict)
                    else None,
                }
            )
        out["knowledge_graph_id"] = getattr(decision, "knowledge_graph_id", None) or (
            decision.get("knowledge_graph_id") if isinstance(decision, dict) else None
        )
        out["decision_node_id"] = getattr(decision, "decision_node_id", None) or (
            decision.get("decision_node_id") if isinstance(decision, dict) else None
        )
    return out


def quality_gates(
    inp: InstitutionalReportInput,
    *,
    validation_ok: bool,
    sections_ok: bool,
    evidence_ok: bool,
    reasons_ok: bool,
    decision_ok: bool,
) -> dict[str, bool]:
    return {
        "recommendation_valid": validation_ok and decision_ok and bool(inp.recommendation),
        "confidence_present": isinstance(inp.confidence, int) and 0 <= inp.confidence <= 100,
        "evidence_exists": bool(inp.evidence) and evidence_ok,
        "thesis_exists": bool(inp.thesis),
        "valuation_exists": bool(str(inp.valuation or "").strip()),
        "risk_exists": bool(str(inp.overall_risk or "").strip()),
        "bottom_line_exists": sections_ok,
        "reasons_valid": reasons_ok,
        "section_reasons_complete": reasons_ok,
        "contradicting_evidence_present": reasons_ok,
        "unknowns_present": reasons_ok,
        "decision_valid": decision_ok,
        "enabled": is_enabled(),
    }


def _rejected(
    inp: InstitutionalReportInput,
    errors: list[str],
    gates: dict[str, bool],
    *,
    reasons: list[Any] | None = None,
    decision: Any = None,
) -> InstitutionalReport:
    diagnostics = build_diagnostics(
        inp, reason_count=len(reasons or []), gates=gates, decision=decision
    )
    return InstitutionalReport(
        ok=False,
        workstream_id=IRE_WORKSTREAM_ID,
        version=IRE_VERSION,
        report_type=IRE_REPORT_TYPE,
        ticker=inp.ticker,
        company_name=inp.company_name,
        recommendation=inp.recommendation,
        conviction=inp.conviction,
        confidence=inp.confidence if isinstance(inp.confidence, int) else -1,
        sections=[],
        text="",
        quality_gates=gates,
        validation_errors=list(errors),
        rejected=True,
        llm=False,
        as_of=inp.as_of,
        input_fingerprint=_fingerprint(inp) if inp.ticker else "",
        reasons=list(reasons or []),
        diagnostics=diagnostics,
        reason_graph_text="",
        decision=decision,
    )


def _generate_institutional_decision(inp: InstitutionalReportInput, graph: Any) -> tuple[Any, list[str]]:
    """Decision System owns recommendation — report only renders it (IDS-02 calibrated)."""
    try:
        from institutional_decision.decision_engine import generate_decision
        from institutional_decision.decision_validator import validate_decision
        from institutional_decision import history as decision_history
    except Exception as exc:  # noqa: BLE001
        return None, [f"decision system unavailable: {exc}"]

    prev = decision_history.latest(inp.ticker)
    previous_version = prev.decision_version if prev else 0
    evidence_ids = [e.evidence_id for e in (inp.evidence or ()) if e.evidence_id]
    decision = generate_decision(
        reasons=list(graph.reasons),
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
        return decision, list(validation.errors)

    # IDS-02 — replace opaque confidence with calibrated confidence
    try:
        from institutional_calibration.calibration_engine import calibrate_decision
        from institutional_calibration.diagnostics import validate_calibration_gates
        from institutional_calibration.flags import is_enabled as cal_enabled

        if cal_enabled():
            decision, bundle = calibrate_decision(
                decision,
                reasons=list(graph.reasons),
                evidence=inp,
                previous=prev,
            )
            cal_errors = validate_calibration_gates(bundle.quality_gates)
            if cal_errors:
                return decision, cal_errors
    except Exception as exc:  # noqa: BLE001
        return decision, [f"calibration failed: {exc}"]

    # KG-01 — attach DecisionNode / graph ids (single-company knowledge graph)
    try:
        from dataclasses import replace as dc_replace

        from institutional_graph.flags import is_enabled as kg_enabled
        from institutional_graph.graph import build_company_graph
        from institutional_graph.impact import compute_impacts
        from institutional_graph.inference import infer
        from institutional_graph.production import _GRAPHS

        if kg_enabled():
            kg = build_company_graph(inp, reasons=list(graph.reasons), decision=decision)
            infer(kg)
            compute_impacts(kg, inp)
            decision = dc_replace(
                decision,
                knowledge_graph_id=kg.graph_id,
                decision_node_id=kg.decision_node_id,
            )
            _GRAPHS[str(inp.ticker or "").strip().upper()] = kg
    except Exception as exc:  # noqa: BLE001
        return decision, [f"knowledge graph failed: {exc}"]

    decision_history.record(decision)
    return decision, []


def compose_report(
    report_input: Union[InstitutionalReportInput, dict[str, Any], None],
) -> InstitutionalReport:
    """Compose a deterministic InstitutionalReport.

    Pipeline: Facts → Reasons → Institutional Decision → Report render.
    Reports do not create recommendations; they render InstitutionalDecision.
    """
    if isinstance(report_input, InstitutionalReportInput):
        inp = report_input
    else:
        inp = InstitutionalReportInput.from_dict(report_input or {})

    validation = validate_input(inp)
    if not validation.ok:
        gates = quality_gates(
            inp,
            validation_ok=False,
            sections_ok=False,
            evidence_ok=False,
            reasons_ok=False,
            decision_ok=False,
        )
        return _rejected(inp, validation.errors, gates)

    # Reasons from factual inputs (BQ/FQ/valuation/risk/thesis) — not from report-owned rec.
    graph = compose_reasons(inp)
    reason_validation = validate_reasons(graph)
    if not reason_validation.ok:
        gates = quality_gates(
            inp,
            validation_ok=True,
            sections_ok=False,
            evidence_ok=False,
            reasons_ok=False,
            decision_ok=False,
        )
        return _rejected(inp, reason_validation.errors, gates, reasons=list(graph.reasons))

    if len(inp.evidence) == 0:
        gates = quality_gates(
            inp,
            validation_ok=True,
            sections_ok=False,
            evidence_ok=False,
            reasons_ok=True,
            decision_ok=False,
        )
        return _rejected(inp, ["evidence count zero"], gates, reasons=list(graph.reasons))

    decision, decision_errors = _generate_institutional_decision(inp, graph)
    if decision_errors:
        gates = quality_gates(
            inp,
            validation_ok=True,
            sections_ok=False,
            evidence_ok=True,
            reasons_ok=True,
            decision_ok=False,
        )
        return _rejected(
            inp, decision_errors, gates, reasons=list(graph.reasons), decision=decision
        )

    # Report consumes decision — overwrite recommendation fields from Decision System.
    render_input = replace(
        inp,
        recommendation=decision.recommendation,
        conviction=decision.conviction,
        confidence=int(decision.confidence),
        horizon=decision.investment_horizon,
    )
    render_graph = compose_reasons(render_input)
    render_reason_validation = validate_reasons(render_graph)
    if not render_reason_validation.ok:
        gates = quality_gates(
            render_input,
            validation_ok=True,
            sections_ok=False,
            evidence_ok=True,
            reasons_ok=False,
            decision_ok=True,
        )
        return _rejected(
            render_input,
            render_reason_validation.errors,
            gates,
            reasons=list(render_graph.reasons),
            decision=decision,
        )

    sections = render_sections_from_reasons(render_graph, render_input)
    section_keys = [s.key for s in sections]
    missing = [k for k in REPORT_SECTIONS if k not in section_keys]
    if missing or len(sections) != len(REPORT_SECTIONS):
        gates = quality_gates(
            render_input,
            validation_ok=True,
            sections_ok=False,
            evidence_ok=True,
            reasons_ok=True,
            decision_ok=True,
        )
        return _rejected(
            render_input,
            [f"missing sections: {missing}"],
            gates,
            reasons=list(render_graph.reasons),
            decision=decision,
        )

    for section in sections:
        if section.reason is None:
            gates = quality_gates(
                render_input,
                validation_ok=True,
                sections_ok=False,
                evidence_ok=True,
                reasons_ok=False,
                decision_ok=True,
            )
            return _rejected(
                render_input,
                [f"section missing reason: {section.key}"],
                gates,
                reasons=list(render_graph.reasons),
                decision=decision,
            )

    text = render_text(sections, ticker=render_input.ticker, company_name=render_input.company_name)
    if "Bottom Line" not in text:
        gates = quality_gates(
            render_input,
            validation_ok=True,
            sections_ok=False,
            evidence_ok=True,
            reasons_ok=True,
            decision_ok=True,
        )
        return _rejected(
            render_input,
            ["bottom line missing from rendered text"],
            gates,
            reasons=list(render_graph.reasons),
            decision=decision,
        )

    gates = quality_gates(
        render_input,
        validation_ok=True,
        sections_ok=True,
        evidence_ok=True,
        reasons_ok=True,
        decision_ok=True,
    )
    if not all(gates.values()):
        failed = [k for k, v in gates.items() if not v]
        return _rejected(
            render_input,
            [f"quality gate failed: {failed}"],
            gates,
            reasons=list(render_graph.reasons),
            decision=decision,
        )

    diagnostics = build_diagnostics(
        render_input,
        reason_count=len(render_graph.reasons),
        gates=gates,
        decision=decision,
    )
    reason_graph_text = render_reason_graph_text(render_graph)

    # KG-01 — reports consume graph-backed lineage / reasons
    kg_summary = None
    try:
        from institutional_graph.production import _GRAPHS
        from institutional_graph.traversal import decision_chain, evidence_chain
        from institutional_reporting.reasoning import Reason

        kg = _GRAPHS.get(str(render_input.ticker or "").strip().upper())
        if kg is not None:
            diagnostics["knowledge_graph"] = {
                "graph_id": kg.graph_id,
                "entity_count": len(kg.nodes),
                "relationship_count": len(kg.relationships),
                "inference_count": len(kg.inferred_relationship_ids),
                "decision_chain": decision_chain(kg),
                "lineage": list(kg.lineage),
                "impact_scores": dict((kg.meta or {}).get("impact_scores") or {}),
            }
            # Enrich reasons with graph evidence chains (no English generation)
            enriched: list[Any] = []
            for reason in render_graph.reasons:
                reason_nodes = [
                    n
                    for n in kg.nodes_by_type("Reason")
                    if (n.attributes or {}).get("section_key") == reason.section_key
                ]
                extra_ids: list[str] = []
                if reason_nodes:
                    for eid in evidence_chain(kg, reason_nodes[0].id):
                        ev = kg.get(eid)
                        if ev and ev.attributes.get("evidence_id"):
                            extra_ids.append(str(ev.attributes["evidence_id"]))
                merged = tuple(
                    dict.fromkeys(list(reason.supporting_evidence or ()) + extra_ids)
                )
                if merged != tuple(reason.supporting_evidence or ()):
                    enriched.append(
                        Reason(
                            title=reason.title,
                            conclusion=reason.conclusion,
                            confidence=reason.confidence,
                            supporting_evidence=merged,
                            supporting_points=reason.supporting_points,
                            contradicting_points=reason.contradicting_points,
                            unknowns=reason.unknowns,
                            section_key=reason.section_key,
                        )
                    )
                else:
                    enriched.append(reason)
            render_graph.reasons = enriched
            kg_summary = {
                "graph_id": kg.graph_id,
                "ticker": kg.ticker,
                "entity_count": len(kg.nodes),
                "relationship_count": len(kg.relationships),
                "inference_count": len(kg.inferred_relationship_ids),
                "decision_node_id": kg.decision_node_id,
                "lineage": list(kg.lineage),
                "impact": dict((kg.meta or {}).get("impact_scores") or {}),
            }
    except Exception:  # noqa: BLE001
        kg_summary = None

    # FG-01 — reports consume forecast scenario comparison (deterministic)
    try:
        from institutional_forecasting.flags import is_enabled as fg_enabled
        from institutional_forecasting.production import run_company_scenarios

        if fg_enabled():
            forecast = run_company_scenarios(
                render_input.ticker,
                scenarios=["base", "bull", "bear"],
                include_graph=False,
                include_propagation=False,
                include_sensitivity=True,
            )
            if forecast.get("ok"):
                diagnostics["forecast_scenarios"] = {
                    "comparison": forecast.get("comparison") or [],
                    "probability_distribution": forecast.get("probability_distribution") or {},
                    "sensitivity": (forecast.get("sensitivity") or {}).get("scorecard") or {},
                    "lineage": forecast.get("lineage") or [],
                }
    except Exception:  # noqa: BLE001
        pass

    return InstitutionalReport(
        ok=True,
        workstream_id=IRE_WORKSTREAM_ID,
        version=IRE_VERSION,
        report_type=IRE_REPORT_TYPE,
        ticker=render_input.ticker,
        company_name=render_input.company_name,
        recommendation=decision.recommendation,
        conviction=decision.conviction,
        confidence=int(decision.confidence),
        sections=sections,
        text=text,
        quality_gates=gates,
        validation_errors=[],
        rejected=False,
        llm=False,
        as_of=render_input.as_of or diagnostics["generated_at"],
        input_fingerprint=_fingerprint(render_input),
        reasons=list(render_graph.reasons),
        diagnostics=diagnostics,
        reason_graph_text=reason_graph_text,
        decision=decision,
        knowledge_graph=kg_summary,
    )
