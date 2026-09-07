"""Production hardening — derived fundamentals, risk, universe, adversarial."""

from __future__ import annotations

from institutional_reasoning.adversarial_suite import run_adversarial_suite
from institutional_reasoning.baselines import run_baseline_suite
from institutional_reasoning.cal.overlays import contextual_confidence
from institutional_reasoning.evidence_validation import validate_contract
from institutional_reasoning.fundamentals.production import quality_gates as fund_gates
from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics
from institutional_reasoning.fundamentals.universe import tier_report
from institutional_reasoning.institutional_evidence.production import package_for_governance as ie_pack
from institutional_reasoning.interrogate import evidence_pack, portfolio_view
from institutional_reasoning.ipi.production import package_for_governance as ipi_pack
from institutional_reasoning.ipi.risk import compute_risk


def test_derived_fundamentals_reproducible():
    gates = fund_gates()
    assert gates["passed"] is True
    assert gates["verified"] == gates["checks"]


def test_derived_risk_metrics_for_infy():
    risk = derive_risk_metrics("INFY")
    assert risk is not None
    assert risk["risk_drivers"]["volatility_ann_pct"] > 10
    assert risk["downside"]["var_95_monthly_pct"] > 0
    assert risk["provider"] == "derived_risk_producer"


def test_ipi_risk_uses_derived_producer():
    r = compute_risk(entity_id="INFY", candidate_weight=0.08)
    assert r["provider"] == "derived_risk_producer"
    assert r["var"] > 0
    assert r["expected_shortfall"] > 0
    assert "risk_drivers" in r


def test_risk_contract_complete_with_derived_packs():
    ie = ie_pack("INFY")
    ipi = ipi_pack("INFY", existing_packs={"institutional_evidence": ie})
    v = validate_contract(
        question_type="risk",
        entity_id="INFY",
        packs={"institutional_evidence": ie, "institutional_portfolio": ipi},
    )
    assert v["complete"] is True
    assert not v.get("missing")
    assert ie.get("risk_drivers")


def test_universe_coverage_reports_gaps():
    # Sprint 2: Nifty 50 is fully panelled; honesty remains on Nifty 500 / global.
    report = tier_report("nifty_50")
    assert report["declared"] == 50
    assert report["by_level"]["full"] == 50
    assert report["by_level"]["uncovered"] == 0
    assert report["honest_gap"]["nifty_500_full_panel"] is False
    n500 = tier_report("nifty_500")
    assert n500["honest_gap"]["nifty_500_full_panel"] is False


def test_contextual_confidence_sector_regime_horizon():
    c = contextual_confidence(
        "hist_multiples", sector="it_services", regime="crisis", horizon="1m"
    )
    assert c["value"] < c["base"]["dynamic"]
    assert c["sector_specific"] == "it_services"


def test_external_baseline_suite():
    suite = run_baseline_suite()
    assert suite["gate_passed"] is True


def test_adversarial_suite_gate():
    suite = run_adversarial_suite()
    assert suite["gate_passed"] is True
    assert suite["passed"] == suite["n"]


def test_interrogate_surfaces():
    ep = evidence_pack("INFY")
    assert ep["found"] is True
    assert "risk_drivers" in ep["validated_fields"] or ep.get("risk_drivers")
    pv = portfolio_view("INFY")
    assert pv["decision"]["action"] in {
        "Increase",
        "Hold",
        "Reduce",
        "Watch",
        "Exit",
        "Replace",
        "Hedge",
        "Withhold",
    }
