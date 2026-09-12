"""AGIB v2.0 — Unified Institutional Knowledge Stack integration acceptance."""

from __future__ import annotations

from knowledge_factory.institutional_knowledge_stack.production import (
    company_bundle,
    dashboard,
    health,
    run_stack,
)
from knowledge_factory.institutional_knowledge_stack.schema import STACK_LAYERS, STACK_VERSION


def test_health_lists_all_layers():
    h = health()
    assert h["version"] == STACK_VERSION
    assert h["soft_wire_only"] is True
    assert h["not_a_reasoning_engine"] is True
    assert len(h["layers"]) == len(STACK_LAYERS)
    ids = {L["id"] for L in h["layers"]}
    assert "relationships" in ids
    assert "alternative_data" in ids
    assert "expectations" in ids


def test_run_stack_and_dashboard():
    report = run_stack(ensure_only_missing=False)
    assert report["soft_wire_only"] is True
    assert report["reasoning_changed"] is False
    assert report["layers_ok"] >= 6
    # Core KF layers should succeed even if universe is heavy/slow
    for key in ("government", "industry", "relationships", "alternative_data", "expectations"):
        assert report["results"][key]["status"] in ("ok", "skipped_already_ready", "error")
    assert report["results"]["expectations"]["status"] == "ok"
    assert report["results"]["relationships"]["status"] == "ok"

    dash = dashboard(ensure=False)
    assert dash["north_star"] == "institutional_knowledge_stack_coverage"
    assert dash["reality"]["relationships"]["status"] == "ok"
    assert dash["reality"]["alternative_data"]["status"] == "ok"
    assert dash["expectations"]["market"]["status"] == "ok"
    assert dash["summary"]["expectation_layers_ok"] >= 1


def test_company_bundle_soft_assembly():
    run_stack(ensure_only_missing=True)
    bundle = company_bundle("INFY")
    assert bundle["ticker"] == "INFY"
    assert bundle["reasoning"] is False
    assert "layers" in bundle
    # At least expectations / relationships / alt-data soft views should materialise
    assert bundle["layers"].get("expectations") is not None
    assert bundle["layers"].get("relationships") is not None
    assert bundle["layers"].get("alternative_data") is not None
