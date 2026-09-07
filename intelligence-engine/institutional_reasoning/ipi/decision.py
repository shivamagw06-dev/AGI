"""Phase 5 decision orchestrator — research package → portfolio decision."""

from __future__ import annotations

import uuid
from typing import Any

from institutional_reasoning.ipi.committee import convene_portfolio_committee
from institutional_reasoning.ipi.evidence import build_portfolio_evidence_pack
from institutional_reasoning.ipi.exposure import compute_exposure
from institutional_reasoning.ipi.memory import remember
from institutional_reasoning.ipi.pdg import build_portfolio_decision_graph
from institutional_reasoning.ipi.policy import evaluate_policy
from institutional_reasoning.ipi.portfolio_book import default_book
from institutional_reasoning.ipi.risk import compute_risk
from institutional_reasoning.ipi.scenarios import compute_scenarios
from institutional_reasoning.ipi.schema import IPI_VERSION, MODULE_CODE, PROGRAMME
from institutional_reasoning.ipi.sizing import size_position

DECISION_VERSION = "portfolio-decision-v1.0.0"


def decide_portfolio(
    *,
    entity_id: str | None,
    entity_name: str | None = None,
    research_record: dict[str, Any] | None = None,
    existing_packs: dict[str, dict[str, Any]] | None = None,
    book: dict[str, Any] | None = None,
    proposed_weight: float | None = None,
    persist_memory: bool = True,
    track_outcome: bool = True,
) -> dict[str, Any]:
    """Full Phase 5 pipeline from research context to portfolio decision."""
    run_id = f"ipi_{uuid.uuid4().hex[:16]}"
    book = book or default_book()
    research_record = research_record or {}

    # First pass pack (current weight) for risk/exposure baselines
    pep = build_portfolio_evidence_pack(
        entity_id,
        entity_name=entity_name,
        research_record=research_record,
        existing_packs=existing_packs,
        book=book,
        proposed_weight=proposed_weight,
        djg_reference=(research_record.get("justification_graph") or {}).get("run_id")
        or research_record.get("run_id"),
    )

    downside = pep.get("downside_intel") or {}
    risk = pep.get("risk") or {}
    exposure = pep.get("exposure_intel") or {}

    # Provisional sizing to feed policy, then re-size under caps
    provisional = size_position(
        entity_id=entity_id,
        evidence=pep.get("evidence_fields") or {},
        downside=downside,
        risk=risk,
        exposure=exposure,
        policy_eval={"policy": book.get("policy") or {}, "capped_weight": 0.07, "breaches": []},
        research_confidence=pep.get("research_confidence"),
        book=book,
    )
    target = float(provisional.get("target_weight") or 0.0)

    # Recompute exposure/risk at proposed target
    exposure = compute_exposure(entity_id=entity_id, proposed_weight=target, book=book)
    risk = compute_risk(entity_id=entity_id, book=book, candidate_weight=target, downside=downside)
    policy_eval = evaluate_policy(
        entity_id=entity_id,
        proposed_weight=target,
        exposure=exposure,
        risk=risk,
        book=book,
    )
    sizing = size_position(
        entity_id=entity_id,
        evidence=pep.get("evidence_fields") or {},
        downside=downside,
        risk=risk,
        exposure=exposure,
        policy_eval=policy_eval,
        research_confidence=pep.get("research_confidence"),
        book=book,
    )
    # Final exposure at sized target
    final_w = float(sizing.get("target_weight") or 0.0)
    exposure = compute_exposure(entity_id=entity_id, proposed_weight=final_w, book=book)
    risk = compute_risk(entity_id=entity_id, book=book, candidate_weight=final_w, downside=downside)
    policy_eval = evaluate_policy(
        entity_id=entity_id,
        proposed_weight=final_w,
        exposure=exposure,
        risk=risk,
        book=book,
    )

    scenarios = compute_scenarios(
        entity_id=entity_id,
        downside=downside,
        exposure=exposure,
        evidence=pep.get("evidence_fields") or {},
    )
    committee = convene_portfolio_committee(
        sizing=sizing,
        policy_eval=policy_eval,
        risk=risk,
        exposure=exposure,
        scenarios=scenarios,
        research_record=research_record,
        downside=downside,
        portfolio_evidence=pep,
    )

    pep["conviction"] = sizing.get("conviction")
    pep["risk_contribution"] = risk.get("risk_contribution")
    pep["exposure_impact"] = (exposure.get("exposure") or {}).get("sector_weight_after")
    pep["expected_return"] = sizing.get("expected_return") if sizing.get("expected_return") is not None else pep.get("expected_return")

    withheld = bool(sizing.get("withheld") or committee.get("action") == "Withhold" or not downside.get("computable"))
    # Unsupported = recommending Increase/Reduce/etc without required evidence
    unsupported = bool(committee.get("can_recommend") and withheld)
    if committee.get("action") == "Withhold":
        unsupported = False

    decision = {
        "run_id": run_id,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IPI_VERSION,
        "decision_version": DECISION_VERSION,
        "entity_id": str(entity_id or "").upper() or None,
        "entity_name": entity_name,
        "research_run_id": research_record.get("run_id"),
        "djg_reference": pep.get("djg_reference"),
        "portfolio_snapshot": {
            "portfolio_id": book.get("portfolio_id"),
            "cash_weight": book.get("cash_weight"),
            "holdings_count": len(book.get("holdings") or []),
        },
        "portfolio_evidence": pep,
        "risk": risk,
        "exposure": exposure,
        "scenarios": scenarios,
        "policy": policy_eval,
        "sizing": sizing,
        "committee": committee,
        "withheld": withheld,
        "unsupported": unsupported,
        "recommendation": {
            "action": committee.get("action"),
            "target_weight": committee.get("target_weight"),
            "maximum_weight": committee.get("maximum_weight"),
            "minimum_weight": committee.get("minimum_weight"),
            "conviction": committee.get("conviction"),
            "confidence": committee.get("confidence"),
            "conclusion": committee.get("conclusion"),
            "replace_candidate": (policy_eval or {}).get("replace_candidate"),
        },
    }
    decision["portfolio_decision_graph"] = build_portfolio_decision_graph(decision)
    if persist_memory:
        remember(decision)
    # Phase 6 — register decision lifecycle (measure later; no learning).
    if track_outcome:
        try:
            from institutional_reasoning.ioi.pipeline import track_decision

            tracked = track_decision(decision, research_record=research_record)
            decision["ioi"] = {
                "decision_id": tracked.get("decision_id"),
                "status": tracked.get("status"),
                "tracked": bool(tracked.get("found")),
            }
        except Exception:
            decision["ioi"] = {"tracked": False}
    return decision
