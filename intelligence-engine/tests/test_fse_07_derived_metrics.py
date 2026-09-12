"""FSE-07 — Derived Metrics Engine tests."""

from __future__ import annotations

import json

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.derived_metrics.calculation.engine import (
    CalculationError,
    calculate_company,
    evaluate_expression,
)
from financial_statements_engine.derived_metrics.dependency.graph import impacted_metrics
from financial_statements_engine.derived_metrics.formula_registry.formulas import FORMULAS, build_registry
from financial_statements_engine.derived_metrics.formula_registry.registry import resolve_order
from financial_statements_engine.derived_metrics.production import (
    calculate,
    contract,
    contracts,
    dashboard,
    formulas,
    health,
    lineage,
)
from financial_statements_engine.derived_metrics.restatement.recalc import recalculate_for_changed_facts
from financial_statements_engine.derived_metrics.schema import METRIC_CONTRACTS, WORKSTREAM_ID
from financial_statements_engine.derived_metrics.store.versions import load_latest, load_version, next_metric_version
from financial_statements_engine.events import EVENT_TYPES
from financial_statements_engine.financial_warehouse.publisher.publish import publish_validated_pack
from financial_statements_engine.parsing.production import parse_bytes
from financial_statements_engine.validation.pipeline import validate_draft


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _facts() -> list[dict]:
    return [
        {"fact_id": "fact:rev", "canonical_metric": "revenue", "metric": "revenue", "value": 100.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:cogs", "canonical_metric": "cogs", "metric": "cogs", "value": 40.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:ebit", "canonical_metric": "ebit", "metric": "ebit", "value": 30.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:ebitda", "canonical_metric": "ebitda", "metric": "ebitda", "value": 35.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:ni", "canonical_metric": "net_income", "metric": "net_income", "value": 20.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:eq", "canonical_metric": "total_equity", "metric": "total_equity", "value": 120.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:ta", "canonical_metric": "total_assets", "metric": "total_assets", "value": 200.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:cl", "canonical_metric": "current_liabilities", "metric": "current_liabilities", "value": 50.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:ca", "canonical_metric": "current_assets", "metric": "current_assets", "value": 80.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:inv", "canonical_metric": "inventory", "metric": "inventory", "value": 10.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:cash", "canonical_metric": "cash", "metric": "cash", "value": 30.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:debt", "canonical_metric": "total_debt", "metric": "total_debt", "value": 40.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:tl", "canonical_metric": "total_liabilities", "metric": "total_liabilities", "value": 80.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:ocf", "canonical_metric": "operating_cash_flow", "metric": "operating_cash_flow", "value": 25.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:capex", "canonical_metric": "capex", "metric": "capex", "value": 5.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:tax", "canonical_metric": "tax_expense", "metric": "tax_expense", "value": 8.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:pbt", "canonical_metric": "profit_before_tax", "metric": "profit_before_tax", "value": 28.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:fc", "canonical_metric": "finance_cost", "metric": "finance_cost", "value": 2.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:sh", "canonical_metric": "shares_outstanding", "metric": "shares_outstanding", "value": 10.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
        {"fact_id": "fact:rec", "canonical_metric": "receivables", "metric": "receivables", "value": 15.0, "reporting_period": "2025-03-31", "company_id": "nse:TCS"},
    ]


def _rich_pack() -> bytes:
    return json.dumps(
        {
            "fields": {
                "Revenue From Operations": {"value": 100.0, "unit_scale": "crores"},
                "PAT": {"value": 20.0, "unit_scale": "crores"},
                "PBT": {"value": 28.0, "unit_scale": "crores"},
                "TaxExpense": {"value": 8.0, "unit_scale": "crores"},
                "CashAndCashEquivalents": {"value": 30.0, "unit_scale": "crores"},
                "TotalAssets": {"value": 200.0, "unit_scale": "crores"},
                "TotalEquity": {"value": 120.0, "unit_scale": "crores"},
                "TotalLiabilities": {"value": 80.0, "unit_scale": "crores"},
                "NetCashFlowsFromUsedInOperatingActivities": {"value": 25.0, "unit_scale": "crores"},
            }
        },
        sort_keys=True,
    ).encode("utf-8")


def test_dme_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["consumes_only_warehouse_facts"] is True
    assert h["never_mutates_warehouse_facts"] is True
    assert h["never_consumes_drafts_or_raw"] is True
    assert "dcf_metrics.v1" in h["contracts"]
    assert h["formulas_n"] >= 10


def test_formula_unicity():
    reg = build_registry()
    assert len(reg) == len(FORMULAS)
    names = [f["metric_name"] for f in FORMULAS]
    assert len(names) == len(set(names))


def test_resolve_order_includes_deps():
    order = resolve_order(["roic"])
    assert order.index("nopat") < order.index("roic")


def test_evaluate_expression_div_zero():
    with pytest.raises(CalculationError) as ei:
        evaluate_expression({"div": ["revenue", "cogs"]}, {"revenue": 1.0, "cogs": 0.0})
    assert ei.value.code == "DIV_ZERO"


def test_calculate_deterministic(fse_tmp):
    a = calculate_company("TCS", facts=_facts())
    b = calculate_company("TCS", facts=_facts())
    assert a["metrics_calculated"] == b["metrics_calculated"]
    assert a["metrics"]["gross_margin"]["value"] == pytest.approx(0.6)
    assert a["metrics"]["roe"]["value"] == pytest.approx(20.0 / 120.0)
    assert a["metrics"]["free_cash_flow"]["value"] == pytest.approx(20.0)
    assert a["metrics"]["gross_margin"]["fingerprint"] == b["metrics"]["gross_margin"]["fingerprint"]
    assert a["mutates_warehouse_facts"] is False


def test_persist_immutable_versions(fse_tmp):
    out1 = calculate("TCS", persist=True, facts=_facts())
    assert out1["persisted"]["stored_n"] >= 1
    company_id = "nse:TCS"
    period = "2025-03-31"
    calculate("TCS", persist=True, facts=_facts())
    v1 = load_version(company_id, period, "gross_margin", 1)
    v2 = load_version(company_id, period, "gross_margin", 2)
    assert v1 is not None and v2 is not None
    assert v1["metric_version"] == 1
    assert v2["metric_version"] == 2
    assert next_metric_version(company_id, period, "gross_margin") == 3
    latest = load_latest(company_id, period, "gross_margin")
    assert latest["metric_version"] == 2


def test_lineage_and_impact(fse_tmp):
    lin = lineage("roic")
    assert lin["found"] is True
    assert any(p.get("metric") == "nopat" for p in lin["path"])
    impacted = impacted_metrics(["revenue"])
    assert "gross_margin" in impacted
    assert "ebit_margin" in impacted


def test_contracts(fse_tmp):
    calculate("TCS", persist=True, facts=_facts())
    assert contracts()["ok"] is True
    for cid in METRIC_CONTRACTS:
        assert cid in contracts()["contracts"]
    dcf = contract("dcf_metrics.v1", "TCS")
    assert dcf["ok"] is True
    assert dcf["direct_storage_access"] is False
    assert "free_cash_flow" in dcf["data"]["metrics"]
    scr = contract("screening_metrics.v1", "TCS")
    assert "roe" in scr["data"]["metrics"]


def test_restatement_recalculation(fse_tmp):
    calculate("TCS", persist=True, facts=_facts())
    # change revenue → new metric versions
    facts2 = _facts()
    for f in facts2:
        if f["metric"] == "revenue":
            f["value"] = 200.0
            f["fact_id"] = "fact:rev2"
    out = recalculate_for_changed_facts("TCS", ["revenue"], facts=facts2)
    assert out["recalculated"] is True
    assert "gross_margin" in out["impacted"]
    gm = load_latest("nse:TCS", "2025-03-31", "gross_margin")
    assert gm is not None
    assert gm["value"] == pytest.approx((200.0 - 40.0) / 200.0)
    assert gm["metric_version"] >= 2


def test_events_registered():
    assert "derived_metrics.calculated.v1" in EVENT_TYPES
    assert "derived_metrics.restatement_recalculated.v1" in EVENT_TYPES


def test_dashboard_and_formulas(fse_tmp):
    calculate("TCS", persist=True, facts=_facts())
    dash = dashboard()
    assert dash["dme_health"] == "ok"
    f = formulas(category="profitability")
    assert f["n"] >= 1
    events = {e["event_type"] for e in get_bus().tail(100)}
    assert "derived_metrics.published.v1" in events


def test_pipeline_warehouse_to_dme(fse_tmp):
    draft = parse_bytes(
        "INFY",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:dme1",
    )
    result = validate_draft(draft)
    assert result["approval"]["publishable"] is True
    # DME from warehouse facts (may calculate subset depending on mapped metrics)
    out = calculate("INFY", persist=True)
    assert out["calculation"]["ok"] is True
    assert out["calculation"]["mutates_warehouse_facts"] is False


def test_missing_inputs_fail_deterministically(fse_tmp):
    sparse = [{"fact_id": "fact:r", "metric": "revenue", "canonical_metric": "revenue", "value": 10.0, "reporting_period": "2025-03-31", "company_id": "nse:X"}]
    calc = calculate_company("X", metrics=["gross_margin"], facts=sparse)
    assert calc["metrics_calculated"] == 0
    assert any(f["code"] == "MISSING_MANDATORY_INPUTS" for f in calc["failures"])


def test_warehouse_restatement_triggers_dme(fse_tmp):
    from financial_statements_engine.financial_warehouse.restatements.engine import record_restatement

    pack = {
        "approval_status": "APPROVED",
        "validation_id": "val:dme-rst",
        "ticker": "TCS",
        "period_end": "2025-03-31",
        "facts": [
            {"metric": "revenue", "value": 100.0, "statement_type": "income_statement"},
            {"metric": "cogs", "value": 40.0, "statement_type": "income_statement"},
            {"metric": "net_income", "value": 20.0, "statement_type": "income_statement"},
            {"metric": "total_equity", "value": 120.0, "statement_type": "balance_sheet"},
            {"metric": "total_assets", "value": 200.0, "statement_type": "balance_sheet"},
            {"metric": "operating_cash_flow", "value": 25.0, "statement_type": "cash_flow"},
            {"metric": "capex", "value": 5.0, "statement_type": "cash_flow"},
            {"metric": "cash", "value": 30.0, "statement_type": "balance_sheet"},
            {"metric": "total_debt", "value": 40.0, "statement_type": "balance_sheet"},
            {"metric": "ebit", "value": 30.0, "statement_type": "income_statement"},
            {"metric": "current_liabilities", "value": 50.0, "statement_type": "balance_sheet"},
            {"metric": "current_assets", "value": 80.0, "statement_type": "balance_sheet"},
            {"metric": "inventory", "value": 10.0, "statement_type": "balance_sheet"},
        ],
    }
    # seed warehouse + initial DME
    publish_validated_pack(validated_pack=pack)
    calculate("TCS", persist=True)
    pack2 = dict(pack)
    pack2["validation_id"] = "val:dme-rst2"
    pack2["facts"] = [{**f, "value": (f["value"] * 1.1 if f["metric"] == "revenue" else f["value"])} for f in pack["facts"]]
    rst = record_restatement(validated_pack=pack2, restatement_reason="correction", original_validation_id="val:dme-rst")
    assert rst.get("published") is True
    assert rst.get("dme_recalculation", {}).get("recalculated") is True
