"""E2E-01 — Institutional Product Experience Validation tests."""

from __future__ import annotations

from product_experience_validation.production import dashboard, health, run
from product_experience_validation.schema import (
    E2E_WORKSTREAM_ID,
    PASS_SCORE,
    PRIMARY_TICKER,
    PRODUCT_ENTRY,
    RUBRIC_WEIGHTS,
)
from product_experience_validation import store as e2e_store


def setup_function(_fn=None):
    e2e_store.reset_for_tests()


def test_health_role_and_brand():
    h = health()
    assert h["workstream_id"] == E2E_WORKSTREAM_ID
    assert h["brand"] == "AGI"
    assert h["not_an_engine"] is True
    assert h["not_a_benchmark"] is True
    assert h["not_an_office"] is True
    assert h["product_entry"] == PRODUCT_ENTRY
    assert h["primary_ticker"] == PRIMARY_TICKER
    assert h["pass_score"] == PASS_SCORE
    # Spec weights sum to 105; scorer normalizes to 0–100.
    assert abs(sum(RUBRIC_WEIGHTS.values()) - 105.0) < 0.01


def test_full_product_experience_passes():
    result = run({})
    assert result["workstream_id"] == E2E_WORKSTREAM_ID
    assert result["buy_sell"] is None
    assert result["score"] >= PASS_SCORE, (result.get("summary"), result.get("failure_codes"))
    assert result["passed"] is True, result.get("failure_codes")
    assert result["final_answer"] == "YES"
    assert result["institutionally_ready"] is True
    # No engine jargon leak
    assert "ENGINE_JARGON_LEAK" not in (result.get("failure_codes") or [])
    assert "HALLUCINATED_FACT" not in (result.get("failure_codes") or [])


def test_dashboard_after_run():
    run({})
    d = dashboard()
    assert d["latest"]["passed"] is True
    assert d["latest"]["score"] >= PASS_SCORE


def test_single_workflow_dashboard():
    out = run({"workflow": "WF1"})
    assert out["ok"] is True
    wf = out["workflow"]
    assert wf["workflow"] == "WF1"
    assert all(c.get("ok") for c in wf["checks"]), wf
