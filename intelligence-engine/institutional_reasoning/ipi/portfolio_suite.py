"""Module 10 — Institutional Portfolio Suite (Phase 5 IPS).

Evaluates portfolio decision quality. Exit: ≥95% with 0 unsupported recommendations.
Distinct from Phase 4 Institutional Planning Suite.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.ipi.decision import decide_portfolio
from institutional_reasoning.ipi.portfolio_book import high_it_book, reset_book, set_active_book
from institutional_reasoning.ipi.schema import IPI_VERSION, PHASE5_TARGETS

SUITE_VERSION = "institutional-portfolio-suite-v1.0.0"


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "ipts_001",
            "question": "Should we invest £1,000,000 in Infosys?",
            "entity_id": "INFY",
            "kind": "full_pipeline",
            "expect_action_in": ("Increase", "Hold", "Reduce", "Watch", "Replace", "Hedge"),
            "expect_pdg": True,
            "expect_risk": True,
            "expect_sizing": True,
        },
        {
            "case_id": "ipts_002",
            "question": "Portfolio already has 32% IT — should we add Infosys weight?",
            "entity_id": "INFY",
            "kind": "sector_limit",
            "book": "high_it",
            "expect_sector_breach_or_reduce": True,
        },
        {
            "case_id": "ipts_003",
            "question": "What is the portfolio exposure impact of Nifty Bank?",
            "entity_id": "NIFTYBANK",
            "kind": "no_downside",
            "expect_withhold": True,
            "force_no_evidence": True,
        },
        {
            "case_id": "ipts_004",
            "question": "Should we invest in Infosys given correlated IT holdings TCS?",
            "entity_id": "INFY",
            "kind": "correlation",
            "expect_risk_adjusted": True,
        },
        {
            "case_id": "ipts_005",
            "question": "Should the portfolio increase weight in Persistent Systems?",
            "entity_id": "PERSISTENT",
            "kind": "liquidity",
            "expect_liquidity_cap": True,
        },
        {
            "case_id": "ipts_006",
            "question": "Should we invest in TCS?",
            "entity_id": "TCS",
            "kind": "full_pipeline",
            "expect_pdg": True,
            "expect_action_in": ("Increase", "Hold", "Reduce", "Watch", "Replace", "Hedge", "Withhold", "Exit"),
        },
        {
            "case_id": "ipts_007",
            "question": "Portfolio position sizing for HDFC Bank exposure",
            "entity_id": "HDFCBANK",
            "kind": "portfolio_type",
            "expect_pdg": True,
        },
        {
            "case_id": "ipts_008",
            "question": "Should we invest £500,000 in Wipro?",
            "entity_id": "WIPRO",
            "kind": "full_pipeline",
            "expect_pdg": True,
        },
    ]


def _grade(case: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    reset_book()
    if case.get("book") == "high_it":
        set_active_book(high_it_book())

    try:
        if case.get("force_no_evidence"):
            # Index-like entity without PE seeds → downside not computable
            decision = decide_portfolio(
                entity_id=case.get("entity_id"),
                research_record={"run_id": "suite_no_ev", "justification_graph": {"run_id": "djg_none"}},
                existing_packs={},
                persist_memory=False,
            )
            research = {}
        else:
            research = govern_answer(case["question"], ticker_hint=case.get("entity_id"))
            decision = research.get("ipi") or decide_portfolio(
                entity_id=case.get("entity_id"),
                research_record=research,
                existing_packs={
                    "institutional_evidence": research.get("institutional_evidence") or {},
                },
                persist_memory=False,
            )

        pdg = decision.get("portfolio_decision_graph") or {}
        committee = decision.get("committee") or {}
        sizing = decision.get("sizing") or {}
        risk = decision.get("risk") or {}
        exposure = decision.get("exposure") or {}
        action = committee.get("action") or sizing.get("action")

        # Universal: never unsupported recommendation
        if decision.get("unsupported"):
            failures.append("unsupported_recommendation")
        if action in {"Buy", "Sell", "Accumulate", "Strong Buy"}:
            failures.append(f"forbidden_action={action}")

        if case.get("expect_pdg"):
            if not (pdg.get("integrity") or {}).get("valid"):
                failures.append(f"pdg_invalid:{(pdg.get('integrity') or {}).get('problems')}")
            if not pdg.get("djg_reference") and not decision.get("djg_reference"):
                # allow missing only when research had no djg — still require PDG structure
                if not (pdg.get("nodes")):
                    failures.append("pdg_missing")

        if case.get("expect_risk") and risk.get("risk_contribution") is None:
            failures.append("missing_risk_contribution")

        if case.get("expect_sizing") and sizing.get("target_weight") is None and action != "Withhold":
            failures.append("missing_sizing")

        if case.get("expect_action_in") and action not in case["expect_action_in"]:
            # Withhold is acceptable when evidence incomplete
            if not (decision.get("withheld") and action == "Withhold"):
                failures.append(f"action={action}")

        if case.get("expect_withhold"):
            if action != "Withhold" and not decision.get("withheld"):
                failures.append("expected_withhold")

        if case.get("expect_sector_breach_or_reduce"):
            breached = bool(exposure.get("rejected")) or any(
                b.get("kind") == "sector" for b in (exposure.get("breaches") or [])
            )
            reduced = action in {"Reduce", "Replace", "Watch", "Withhold", "Hold"}
            # Increasing further into 32% IT must not be unconstrained
            if action == "Increase" and not breached:
                # Still OK if target did not raise sector above limit
                after = float(((exposure.get("exposure") or {}).get("sector_weight_after") or 0))
                limit = float(((decision.get("policy") or {}).get("policy") or {}).get("max_sector_weight") or 0.25)
                if after > limit + 1e-9:
                    failures.append("sector_limit_not_enforced")
            elif not (breached or reduced or action in {"Reduce", "Replace"}):
                # If already at limit, Increase should be capped/replaced
                if action == "Increase":
                    after = float(((exposure.get("exposure") or {}).get("sector_weight_after") or 0))
                    limit = float(((decision.get("policy") or {}).get("policy") or {}).get("max_sector_weight") or 0.25)
                    if after > limit + 1e-9:
                        failures.append("sector_overflow_allowed")

        if case.get("expect_risk_adjusted"):
            # Correlated IT peers should elevate risk contribution vs isolated name
            if float(risk.get("risk_contribution") or 0) <= 0:
                failures.append("risk_contribution_not_positive")

        if case.get("expect_liquidity_cap"):
            tw = float(sizing.get("target_weight") or 0)
            if tw > 0.025 + 1e-9 and action not in {"Withhold", "Watch", "Exit"}:
                failures.append(f"liquidity_not_capped:{tw}")

        # PDG coverage for every graded decision
        if not pdg.get("nodes"):
            failures.append("pdg_absent")
        elif (pdg.get("integrity") or {}).get("valid") is not True:
            failures.append("pdg_integrity_failed")

        return {
            "case_id": case["case_id"],
            "kind": case["kind"],
            "passed": not failures,
            "failures": failures,
            "action": action,
            "withheld": decision.get("withheld"),
            "unsupported": decision.get("unsupported"),
            "pdg_valid": (pdg.get("integrity") or {}).get("valid"),
            "target_weight": sizing.get("target_weight"),
            "risk_contribution": risk.get("risk_contribution"),
        }
    finally:
        reset_book()


def run_portfolio_suite() -> dict[str, Any]:
    results = [_grade(c) for c in _cases()]
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    score = round(100.0 * passed / total, 2) if total else 0.0
    unsupported = sum(1 for r in results if r.get("unsupported"))
    pdg_ok = sum(1 for r in results if r.get("pdg_valid"))
    pdg_pct = round(100.0 * pdg_ok / total, 2) if total else 0.0
    gate = {
        "portfolio_suite": score >= PHASE5_TARGETS["portfolio_suite"],
        "pdg_coverage": pdg_pct >= PHASE5_TARGETS["pdg_coverage"],
        "unsupported_recommendations": unsupported <= PHASE5_TARGETS["unsupported_recommendations"],
    }
    return {
        "suite": "Institutional Portfolio Suite",
        "suite_version": SUITE_VERSION,
        "ipi_version": IPI_VERSION,
        "score": score,
        "passed": passed,
        "total": total,
        "unsupported_recommendations": unsupported,
        "pdg_coverage_pct": pdg_pct,
        "phase5_targets": PHASE5_TARGETS,
        "phase5_gate": {
            "passed": all(gate.values()),
            "checks": gate,
        },
        "results": results,
    }
