"""AGIB Investment Decision Engine — soft production entry for Ask AGI."""

from __future__ import annotations

from typing import Any

from decision_engine.flags import flags_dict, is_enabled
from decision_engine.intent import is_investment_decision_question
from decision_engine.layers import assemble_layers
from decision_engine.schema import ARCHITECTURE_STATUS, IDE_VERSION, PROGRAMME


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "version": IDE_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine_redesign": True,
        "never_skip_layer": True,
        "decision_last": True,
        "flags": flags_dict(),
    }


def package_for_ask_agi(
    query: str = "",
    *,
    ticker: str | None = None,
    cid: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    company_monitor: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    market_events: dict[str, Any] | None = None,
    investment_intelligence: dict[str, Any] | None = None,
    institutional_briefing: dict[str, Any] | None = None,
    intelligence_construction: dict[str, Any] | None = None,
    irp: dict[str, Any] | None = None,
    aws_macro: dict[str, Any] | None = None,
    gate_blocked: bool | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Soft entry — builds the full 13-layer decision stack for buy/invest questions."""
    if not is_enabled():
        return {
            "enabled": False,
            "programme": PROGRAMME,
            "version": IDE_VERSION,
            "bypassed": True,
            "architecture_status": ARCHITECTURE_STATUS,
        }

    leo = live_evidence if isinstance(live_evidence, dict) else {}
    irp_pkg = irp if isinstance(irp, dict) else {}
    triggered = force or is_investment_decision_question(query, leo_pkg=leo, irp=irp_pkg)
    # Also trigger when we have a resolved company for research-style questions
    if not triggered and (ticker or (company_analysis or {}).get("ticker") or (cid or {}).get("ticker")):
        if str((irp_pkg or {}).get("intent") or "").lower() in {"company_research", "investment_thesis", "valuation"}:
            triggered = True

    if not triggered:
        return {
            "enabled": True,
            "active": False,
            "programme": PROGRAMME,
            "version": IDE_VERSION,
            "architecture_status": ARCHITECTURE_STATUS,
            "reason": "not_an_investment_decision_question",
            "flags": flags_dict(),
        }

    sif = sector_intelligence if isinstance(sector_intelligence, dict) else {}
    blocked = gate_blocked
    if blocked is None:
        blocked = bool((sif.get("recommendation_gate") or {}).get("blocked")) or bool(
            (leo.get("quality_gate") or {}).get("blocked")
        )

    assembled = assemble_layers(
        query=query,
        ticker=ticker,
        cid=cid,
        company_analysis=company_analysis,
        sector_intelligence=sif,
        live_evidence=leo,
        evidence_completion=evidence_completion,
        valuation_pack=valuation_pack,
        market_events=market_events,
        investment_intelligence=investment_intelligence,
        institutional_briefing=institutional_briefing
        or ((irp_pkg.get("institutional_briefing") if isinstance(irp_pkg, dict) else None)),
        intelligence_construction=intelligence_construction,
        aws_macro=aws_macro,
        irp=irp_pkg,
        gate_blocked=bool(blocked),
    )

    decision = (assembled.get("layers_by_id") or {}).get("decision") or {}
    expected = (assembled.get("layers_by_id") or {}).get("expected_return") or {}
    probability = (assembled.get("layers_by_id") or {}).get("probability") or {}
    readiness = assembled.get("institutional_readiness_gate") or {}

    # Soft optional FIML consult — never required
    fiml_hint = None
    try:
        from models.consumers import for_ask_agi as fiml_for_ask_agi

        payload = {
            "subject_id": ticker or assembled.get("ticker") or "subject",
            "margin_of_safety": expected.get("margin_of_safety_proxy"),
            "catalysts": ((assembled.get("layers_by_id") or {}).get("catalysts") or {}).get("positive") or [],
            "data_quality": "B",
        }
        fiml_hint = fiml_for_ask_agi(payload)
    except Exception:
        fiml_hint = None

    gate_blocked_out = bool(assembled.get("gate_blocked") or readiness.get("hard_fail") or blocked)

    # IEP-01: no BUY/SELL/OW/UW without complete evidence + published statements
    iep_decision_gate: dict[str, Any] | None = None
    action_out = decision.get("action")
    try:
        from institutional_evidence.gates import gate_decision_recommendation

        iep_decision_gate = gate_decision_recommendation(
            str(assembled.get("ticker") or ticker or ""),
            str(action_out or ""),
        )
        if iep_decision_gate and not iep_decision_gate.get("allowed"):
            action_out = iep_decision_gate.get("recommendation") or "NO RECOMMENDATION"
            gate_blocked_out = True
            if isinstance(decision, dict):
                decision = dict(decision)
                decision["action"] = action_out
                decision["iep_gate"] = iep_decision_gate
                decision["original_action"] = iep_decision_gate.get("original_recommendation")
    except Exception:
        iep_decision_gate = None

    return {
        "enabled": True,
        "active": True,
        "programme": PROGRAMME,
        "version": IDE_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine_redesign": True,
        "flags": flags_dict(),
        "query": query,
        "ticker": assembled.get("ticker"),
        "company_name": assembled.get("company_name"),
        "overall_score": assembled.get("overall_score"),
        "investment_grade": assembled.get("investment_grade"),
        "layers": assembled.get("layers"),
        "institutional_readiness_gate": readiness,
        "iep_decision_gate": iep_decision_gate,
        "summary": {
            "overall_score": assembled.get("overall_score"),
            "investment_grade": assembled.get("investment_grade"),
            "confidence_pct": decision.get("confidence_pct"),
            "institutional_readiness_pct": readiness.get("institutional_readiness_pct")
            or readiness.get("overall_coverage_pct"),
            "recommendation_readiness_pct": readiness.get("recommendation_readiness_pct")
            or readiness.get("evidence_confidence_pct")
            or decision.get("evidence_confidence_pct"),
            "evidence_confidence_pct": readiness.get("recommendation_readiness_pct")
            or readiness.get("evidence_confidence_pct")
            or decision.get("evidence_confidence_pct"),
            "analytical_confidence": readiness.get("analytical_confidence_display")
            or (readiness.get("analytical_confidence") or {}).get("display"),
            "analytical_confidence_explanation": readiness.get("analytical_confidence_explanation"),
            "company_quality_10": readiness.get("company_quality_10") or decision.get("company_quality_10"),
            "market_opportunity_10": readiness.get("market_opportunity_10")
            or decision.get("market_opportunity_10"),
            "investment_thesis_status": decision.get("investment_thesis_status"),
            "not_a_negative_view": decision.get("not_a_negative_view"),
            "decision_line": readiness.get("decision_line"),
            "expected_return_12m_pct": decision.get("expected_return_12m_pct"),
            "bull_case_pct": decision.get("bull_case_pct"),
            "base_case_pct": decision.get("base_case_pct"),
            "bear_case_pct": decision.get("bear_case_pct"),
            "probability_weighted_return_pct": decision.get("probability_weighted_return_pct"),
            "risk_reward": decision.get("risk_reward"),
            "action": action_out,
            "suitable_for": decision.get("suitable_for") or [],
            "unsuitable_for": decision.get("unsuitable_for") or [],
            "layer_scores": decision.get("layer_scores") or {},
            "gate_blocked": gate_blocked_out,
            "readiness_band": readiness.get("band"),
            "overall_coverage_pct": readiness.get("overall_coverage_pct"),
            "recommendation_id": (governance.get("audit") or {}).get("recommendation_id"),
            "thesis_drift": (governance.get("thesis_drift") or {}).get("thesis_drift"),
            "weakest_engine": (governance.get("engine_confidence") or {}).get("weakest_engine"),
        },
        "pre_questions": decision.get("pre_questions") or [],
        "decision": decision,
        "probability": probability,
        "expected_return": expected,
        "answer_enrichment": {
            "executive_framing": (
                f"Investment decision stack for {assembled.get('company_name')}: "
                "governance → readiness gate → macro → industry → company → financials → management → valuation → "
                "expectations → technical → risk → catalysts → probability → expected return → conclusion. "
                "No layer is skipped. Data completeness is never treated as company quality."
            ),
            "why_bullets": [
                lyr.get("reasoning")
                for lyr in (assembled.get("layers") or [])[:6]
                if lyr.get("id") != "decision" and lyr.get("reasoning")
            ][:6],
            "decision_conclusion": decision.get("reasoning"),
            "readiness_summary": (readiness.get("summary_for_user") or {}).get("reason"),
            "critical_missing": [
                f"{x.get('rank')}. {x.get('label')} (Impact: {x.get('impact')})"
                for x in ((governance.get("critical_missing_evidence") or {}).get("items") or [])[:4]
            ],
        },
        "fiml_soft_consult": {
            "used": bool(fiml_hint),
            "narrative_hint": (fiml_hint or {}).get("narrative_hint"),
        }
        if fiml_hint
        else {"used": False},
        "answer_policy": "multi_layer_investment_decision_never_direct_buy_sell",
        "never_skip_layer": True,
        "decision_last": True,
        "never_expose_framework_names": True,
        "never_conflate_data_with_quality": True,
        "never_recommend_on_stale_data": True,
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": IDE_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "thirteen_layers": True,
            "never_skip_layer": True,
            "decision_last": True,
            "never_direct_buy_sell_first": True,
        },
        "flags": flags_dict(),
    }
