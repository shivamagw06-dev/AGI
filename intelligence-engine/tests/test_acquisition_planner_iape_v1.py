"""RQ1 Sprint 7 — Institutional Acquisition & API Planning Engine regression tests."""

from acquisition_planner.acquisition_plan import build_acquisition_plan
from acquisition_planner.api_registry import PROVIDERS
from acquisition_planner.production import quality_gates, soft_slice_for_ask_agi
from acquisition_planner.schema import CONFIDENCE_THRESHOLD, MAX_PLANNING_MS_TARGET


def test_hdfc_buy_evidence_plan():
    row = build_acquisition_plan(
        "Should I buy HDFC Bank?",
        {"primary_objective": "decision_support", "intent_family": "company"},
    )
    keys = {r["evidence_key"] for r in row["required_data"]}
    for need in (
        "official_filings",
        "quarterly_results",
        "historical_financials",
        "peer_metrics",
        "macro_data",
        "management_commentary",
        "historical_valuation",
        "portfolio_exposure",
    ):
        assert need in keys
    providers = {s["evidence_key"]: s["provider"] for s in row["selected_providers"]}
    assert providers.get("historical_valuation") in {"groww", "indianapi", "yahoo_finance", "fmp"}
    reuse_providers = {r["provider"] for r in row["reuse_internal_layers"]}
    assert reuse_providers & {"fil", "pil", "ikg", "eil", "ilm"}
    assert row["metrics"]["duplicate_fetches"] == 0
    assert row["metrics"]["api_reduction"] >= 0.3
    assert row["confidence"] >= CONFIDENCE_THRESHOLD
    assert row["authority_plan"]["authority_compliance"] is True


def test_historical_pe_provider_chain():
    row = build_acquisition_plan(
        "Is Infosys overvalued on PE?",
        {"primary_objective": "valuation_assessment"},
    )
    pid = None
    for s in row["selected_providers"]:
        if s["evidence_key"] == "historical_valuation":
            pid = s["provider"]
            break
    if pid is None:
        # may be reused from PIL
        for r in row["reuse_internal_layers"]:
            if r["evidence_key"] == "historical_valuation":
                pid = r["provider"]
    assert pid in {"groww", "indianapi", "yahoo_finance", "fmp", "pil"}


def test_annual_report_prefers_company_ir_or_exchange():
    row = build_acquisition_plan(
        "Should I buy HDFC Bank?",
        {
            "primary_objective": "decision_support",
            "internal_inventory": {
                "fil": {"available": False, "covers": [], "age_hours": 999},
                "pil": {"available": True, "covers": ["peer_metrics"], "age_hours": 12},
                "ikg": {"available": True, "covers": ["knowledge_graph_context"], "age_hours": 6},
                "eil": {"available": True, "covers": ["evidence_corpus"], "age_hours": 4},
                "ilm": {"available": True, "covers": ["portfolio_exposure"], "age_hours": 24},
            },
        },
    )
    filings = next((s for s in row["selected_providers"] if s["evidence_key"] == "official_filings"), None)
    assert filings is not None
    assert filings["provider"] in {"company_ir", "nse", "bse", "sec_edgar", "annual_reports"}


def test_educational_reuses_internal():
    row = build_acquisition_plan(
        "Explain ROIC",
        {"primary_objective": "educational_explanation", "intent_family": "educational"},
    )
    assert len(row["reuse_internal_layers"]) >= 1
    assert len(row["selected_providers"]) <= 2
    assert row["freshness_plan"]["required_freshness"] == "existing_knowledge"


def test_no_duplicate_fetches():
    row = build_acquisition_plan("Should I buy TCS?", {"primary_objective": "decision_support"})
    assert row["metrics"]["duplicate_fetches"] == 0
    seen = set()
    for step in row["executed_acquisitions"]:
        if step["action"] != "acquire":
            continue
        key = (step["evidence_key"], step["provider"])
        assert key not in seen
        seen.add(key)


def test_evidence_budget_caps_api_calls():
    row = build_acquisition_plan(
        "Should I buy HDFC Bank?",
        {
            "primary_objective": "decision_support",
            "evidence_budget": {
                "maximum_api_calls": 2,
                "maximum_runtime_ms": 4000,
                "target_confidence": 0.9,
                "minimum_authority_tier": 2,
            },
            "internal_inventory": {
                "fil": {"available": False, "covers": [], "age_hours": 999},
                "pil": {"available": False, "covers": [], "age_hours": 999},
                "ikg": {"available": False, "covers": [], "age_hours": 999},
                "eil": {"available": False, "covers": [], "age_hours": 999},
                "ilm": {"available": False, "covers": [], "age_hours": 999},
            },
        },
    )
    assert len(row["selected_providers"]) <= 2
    assert row["evidence_budget"]["within_budget"] is True


def test_soft_slice_shape():
    slice_ = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {"primary_objective": "decision_support"})
    assert slice_["not_a_top_level_intelligence_layer"] is True
    assert "required_data" in slice_
    assert "selected_providers" in slice_
    assert "evidence_budget" in slice_


def test_registry_has_sprint_providers():
    for pid in ("groww", "company_ir", "nse", "fred", "fil", "pil", "ikg", "eil", "ilm"):
        assert pid in PROVIDERS


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["checked"] >= 1000
    assert gates["provider_selection_accuracy"] >= 0.99
    assert gates["internal_reuse_accuracy"] >= 1.0
    assert gates["duplicate_api_calls"] == 0
    assert gates["authority_compliance"] >= 1.0
    assert gates["fallback_success"] >= 0.99
    assert gates["average_planning_ms"] < MAX_PLANNING_MS_TARGET
    assert gates["average_api_reduction"] >= 0.30
    assert gates["ok"] is True
