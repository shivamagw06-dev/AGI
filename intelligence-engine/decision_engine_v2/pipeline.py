"""IDE V2 analyse pipeline — constitutional institutional decision orchestration."""

from __future__ import annotations

from typing import Any

from decision_engine_v2.audit.engine import build_and_store_audit, fetch_audit
from decision_engine_v2.confidence.engine import compute_confidence
from decision_engine_v2.conflicts.engine import detect_conflicts
from decision_engine_v2.consensus.engine import consensus_view
from decision_engine_v2.constitution.engine import enforce_constitution
from decision_engine_v2.decision_reasoning.engine import build_reasoning
from decision_engine_v2.evidence_engine.engine import summarise_evidence
from decision_engine_v2.learning_hooks.engine import build_learning_hooks
from decision_engine_v2.monitoring.engine import build_monitoring_plan
from decision_engine_v2.orchestrator.collect import collect_inputs
from decision_engine_v2.recommendation_gate.engine import apply_gate
from decision_engine_v2.reports.build import build_report
from decision_engine_v2.schema import (
    ARCHITECTURE_FROZEN,
    FREEZE_REVIEW,
    IDEV2_VERSION,
    PRIMARY_QUESTION,
)
from decision_engine_v2.store.audit_log import monitoring_for
from decision_engine_v2.uncertainty.engine import classify_uncertainty
from decision_engine_v2.weighting.engine import compute_weights


def analyse_company(
    ticker: str,
    *,
    question: str | None = None,
    committee: dict[str, Any] | None = None,
    portfolio_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q = question or PRIMARY_QUESTION
    inputs = collect_inputs(ticker, question=q)
    if not inputs.get("ticker"):
        return {
            "found": False,
            "ticker": (ticker or "").upper(),
            "idev2_version": IDEV2_VERSION,
            "primary_question": PRIMARY_QUESTION,
        }

    # Soft overlays from live IAF call (no redesign)
    if portfolio_intelligence:
        inputs["layers"]["portfolio_intelligence"] = {
            **(inputs["layers"].get("portfolio_intelligence") or {}),
            **portfolio_intelligence,
        }
    if committee:
        inputs["layers"]["investment_committee"] = {
            **(inputs["layers"].get("investment_committee") or {}),
            **{
                "committee_stance": committee.get("committee_stance") or committee.get("stance"),
                "minority_opinions": committee.get("minority_opinions"),
                "disagreements": committee.get("disagreements") or committee.get("stage_2_conflicts"),
                "disagreement_matrix": committee.get("disagreement_matrix"),
                "present": True,
            },
        }

    evidence = summarise_evidence(inputs)
    weights = compute_weights(inputs, question=q)
    conflicts = detect_conflicts(inputs, committee=committee)
    uncertainty = classify_uncertainty(inputs, conflicts=conflicts, evidence=evidence)
    confidence = compute_confidence(
        evidence=evidence,
        weights=weights,
        conflicts=conflicts,
        uncertainty=uncertainty,
        inputs=inputs,
        committee=committee,
    )
    consensus = consensus_view(inputs, committee=committee, conflicts=conflicts)

    # Provisional pack for constitution checks
    provisional = {
        "evidence_summary": evidence,
        "inputs_present": inputs.get("inputs_present"),
        "reasoning_chain": True,
        "weights": weights,
        "committee_position": consensus.get("committee_position"),
        "committee_present": True,
        "portfolio_context": {
            "net_effect": (inputs.get("stack_summary") or {}).get("portfolio_net_effect"),
            "fit": (inputs.get("stack_summary") or {}).get("portfolio_fit"),
            "quality": (inputs.get("stack_summary") or {}).get("portfolio_quality"),
            "portfolio_id": (inputs.get("stack_summary") or {}).get("portfolio_id"),
        },
        "portfolio_present": True,
        "recommendation_gate": {"pending": True},
        "policy_checked": True,
        "executive_decision": "pending",
        "institutional_judgement": "pending",
    }
    gate = apply_gate(
        evidence=evidence,
        conflicts=conflicts,
        uncertainty=uncertainty,
        confidence=confidence,
        inputs=inputs,
        constitution={"constitutional": True},  # gate first; final constitution after judgement
    )
    reasoning = build_reasoning(
        question=q,
        evidence=evidence,
        weights=weights,
        conflicts=conflicts,
        uncertainty=uncertainty,
        confidence=confidence,
        consensus=consensus,
        gate=gate,
        inputs=inputs,
    )
    monitoring = build_monitoring_plan(
        ticker=inputs["ticker"], gate=gate, inputs=inputs, conflicts=conflicts
    )
    learning_hooks = build_learning_hooks(
        ticker=inputs["ticker"], gate=gate, confidence=confidence, inputs=inputs
    )

    pack: dict[str, Any] = {
        "found": True,
        "ticker": inputs["ticker"],
        "question": q,
        "idev2_version": IDEV2_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "inputs_present": inputs.get("inputs_present"),
        "input_coverage": inputs.get("coverage"),
        "evidence_summary": evidence,
        "weights": weights,
        "conflicts": conflicts,
        "uncertainty": uncertainty,
        "confidence": confidence,
        "committee_position": consensus.get("committee_position"),
        "minority_view": consensus.get("minority_view"),
        "portfolio_context": provisional["portfolio_context"],
        "recommendation_gate": gate,
        "reasoning": reasoning,
        "institutional_judgement": reasoning.get("final_institutional_judgement"),
        "executive_decision": reasoning.get("final_institutional_judgement"),
        "monitoring": monitoring,
        "learning_hooks": learning_hooks,
        "freeze_review": FREEZE_REVIEW,
        "not_an_engine_redesign": True,
        "never_recommendation": True,
        "does_not_replace_analysts": True,
        "does_not_replace_committee": True,
        "does_not_replace_cio": True,
        "orchestrates_all_layers": True,
        "final_architectural_component": True,
    }
    pack["constitution"] = enforce_constitution(pack)
    # Re-check gate if constitution failed
    if not pack["constitution"].get("constitutional"):
        pack["recommendation_gate"] = apply_gate(
            evidence=evidence,
            conflicts=conflicts,
            uncertainty=uncertainty,
            confidence=confidence,
            inputs=inputs,
            constitution=pack["constitution"],
        )
    pack["audit"] = build_and_store_audit(pack)
    pack["report"] = build_report(pack)
    return pack


def analyse_query(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ticker = payload.get("ticker") or payload.get("symbol") or "HDFCBANK"
    question = payload.get("question") or payload.get("query") or PRIMARY_QUESTION
    return analyse_company(
        str(ticker),
        question=str(question),
        committee=payload.get("committee") if isinstance(payload.get("committee"), dict) else None,
        portfolio_intelligence=payload.get("portfolio_intelligence")
        if isinstance(payload.get("portfolio_intelligence"), dict)
        else None,
    )


def monitoring_pack(ticker: str) -> dict[str, Any]:
    rows = monitoring_for(ticker)
    # Ensure at least one live plan by analysing if empty
    if not rows:
        out = analyse_company(ticker)
        rows = monitoring_for(ticker) or [
            {
                "audit_id": (out.get("audit") or {}).get("audit_id"),
                "ticker": out.get("ticker"),
                "monitoring": out.get("monitoring"),
                "recommendation_status": (out.get("recommendation_gate") or {}).get("status"),
            }
        ]
    return {
        "ticker": (ticker or "").upper(),
        "idev2_version": IDEV2_VERSION,
        "monitoring": rows,
        "count": len(rows),
    }


def audit_pack(audit_id: str) -> dict[str, Any]:
    return {"idev2_version": IDEV2_VERSION, **fetch_audit(audit_id)}
