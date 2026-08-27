"""FIRE-02 — Financial Relationship & Driver Analysis tests."""

from __future__ import annotations

from financial_intelligence.drivers.analysis import (
    analyse_balance_sheet,
    analyse_cash_quality,
    analyse_capital_allocation,
    analyse_profitability_drivers,
    analyse_returns,
    analyse_working_capital,
)
from financial_intelligence.drivers.core import make_relationship
from financial_intelligence.drivers.engine import build_driver_pack
from financial_intelligence.drivers.production import drivers, health, relationships
from financial_intelligence.drivers.schema import WORKSTREAM_ID
from financial_intelligence.production import company as fire01_company
from financial_intelligence.production import financial_drivers, financial_relationships
from financial_intelligence.report import build_report


def _pts(metric: str, pairs: list[tuple[str, float]]) -> list[dict]:
    return [
        {
            "metric": metric,
            "period": pe,
            "value": v,
            "version": 1,
            "warehouse_version": "fwh-v1.0.0",
            "validation_status": "APPROVED",
            "validation_id": f"val:{metric}:{pe}",
            "fact_key": f"fk:{metric}:{pe}",
        }
        for pe, v in pairs
    ]


def _base_map(**extra) -> dict:
    m = {
        "revenue": _pts("revenue", [("2024-03-31", 100.0), ("2025-03-31", 120.0)]),
        "gross_profit": _pts("gross_profit", [("2024-03-31", 40.0), ("2025-03-31", 54.0)]),
        "ebitda": _pts("ebitda", [("2024-03-31", 25.0), ("2025-03-31", 32.0)]),
        "ebit": _pts("ebit", [("2024-03-31", 20.0), ("2025-03-31", 28.0)]),
        "net_income": _pts("net_income", [("2024-03-31", 15.0), ("2025-03-31", 18.0)]),
        "operating_margin": _pts("operating_margin", [("2024-03-31", 16.0), ("2025-03-31", 18.5)]),
        "gross_margin": _pts("gross_margin", [("2024-03-31", 40.0), ("2025-03-31", 45.0)]),
        "operating_cash_flow": _pts("operating_cash_flow", [("2024-03-31", 14.0), ("2025-03-31", 12.0)]),
        "free_cash_flow": _pts("free_cash_flow", [("2024-03-31", 10.0), ("2025-03-31", 8.0)]),
        "capex": _pts("capex", [("2024-03-31", 5.0), ("2025-03-31", 6.0)]),
        "working_capital": _pts("working_capital", [("2024-03-31", 20.0), ("2025-03-31", 30.0)]),
        "receivables": _pts("receivables", [("2024-03-31", 10.0), ("2025-03-31", 16.0)]),
        "inventory": _pts("inventory", [("2024-03-31", 8.0), ("2025-03-31", 12.0)]),
        "payables": _pts("payables", [("2024-03-31", 6.0), ("2025-03-31", 7.0)]),
        "cash": _pts("cash", [("2024-03-31", 12.0), ("2025-03-31", 18.0)]),
        "total_debt": _pts("total_debt", [("2024-03-31", 50.0), ("2025-03-31", 40.0)]),
        "total_equity": _pts("total_equity", [("2024-03-31", 80.0), ("2025-03-31", 90.0)]),
        "roe": _pts("roe", [("2024-03-31", 14.0), ("2025-03-31", 16.0)]),
        "roce": _pts("roce", [("2024-03-31", 12.0), ("2025-03-31", 13.5)]),
        "dividends": _pts("dividends", [("2024-03-31", 2.0), ("2025-03-31", 2.5)]),
    }
    m.update(extra)
    return m


def test_fire02_health():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["never_mutates_warehouse"] is True
    assert h["uses_llm"] is False
    assert h["buy_sell"] is False
    assert h["fire_01_unchanged"] is True


def test_revenue_margin_relationships():
    rows = analyse_profitability_drivers(_base_map(), coverage_pct=90)
    codes = {r["code"] for r in rows}
    assert "possible_operating_leverage" in codes or "gross_margin_support" in codes
    assert all(r.get("evidence") for r in rows)


def test_margin_pressure_rule():
    series = _base_map(
        operating_margin=_pts("operating_margin", [("2024-03-31", 20.0), ("2025-03-31", 15.0)]),
    )
    codes = {r["code"] for r in analyse_profitability_drivers(series, coverage_pct=80)}
    assert "margin_pressure" in codes


def test_pat_cash_flow_relationships():
    # OCF lags PAT growth and weak conversion
    series = _base_map(
        net_income=_pts("net_income", [("2024-03-31", 10.0), ("2025-03-31", 20.0)]),
        operating_cash_flow=_pts("operating_cash_flow", [("2024-03-31", 12.0), ("2025-03-31", 8.0)]),
    )
    rows = analyse_cash_quality(series, coverage_pct=85)
    codes = {r["code"] for r in rows}
    assert "weak_cash_conversion" in codes or "profit_not_supported_by_cash" in codes
    assert "ocf_slower_than_pat" in codes or "deteriorating_cash_generation" in codes
    for r in rows:
        assert r["evidence"]
        assert "BUY" not in (r.get("narrative") or "").upper()


def test_debt_trend_deleveraging():
    rows = analyse_balance_sheet(_base_map(), coverage_pct=80)
    codes = {r["code"] for r in rows}
    assert "deleveraging" in codes
    assert "liquidity_improvement" in codes


def test_working_capital_deterioration_and_improvement():
    det = analyse_working_capital(_base_map(), coverage_pct=80)
    codes = {r["code"] for r in det}
    assert "inventory_build" in codes or "receivable_expansion" in codes or "working_capital_pressure" in codes

    improved = _base_map(
        working_capital=_pts("working_capital", [("2024-03-31", 30.0), ("2025-03-31", 20.0)]),
        inventory=_pts("inventory", [("2024-03-31", 12.0), ("2025-03-31", 10.0)]),
        receivables=_pts("receivables", [("2024-03-31", 16.0), ("2025-03-31", 12.0)]),
    )
    codes2 = {r["code"] for r in analyse_working_capital(improved, coverage_pct=80)}
    assert "improving_efficiency" in codes2


def test_capital_allocation_detection():
    series = _base_map(
        capex=_pts("capex", [("2024-03-31", 5.0), ("2025-03-31", 20.0)]),
    )
    codes = {r["code"] for r in analyse_capital_allocation(series, coverage_pct=80)}
    assert "aggressive_expansion" in codes or "shareholder_return_focus" in codes or "balance_sheet_strengthening" in codes


def test_roe_roce_relationships():
    codes = {r["code"] for r in analyse_returns(_base_map(), coverage_pct=80)}
    assert any("roe" in c for c in codes)
    assert any("roce" in c for c in codes)


def test_cash_conversion_quality_strong():
    series = _base_map(
        net_income=_pts("net_income", [("2025-03-31", 10.0)]),
        operating_cash_flow=_pts("operating_cash_flow", [("2025-03-31", 15.0)]),
        free_cash_flow=_pts("free_cash_flow", [("2024-03-31", 8.0), ("2025-03-31", 12.0)]),
    )
    # Need 2 points for growth on fcf; PAT/OCF same period for conversion
    series["net_income"] = _pts("net_income", [("2024-03-31", 9.0), ("2025-03-31", 10.0)])
    series["operating_cash_flow"] = _pts("operating_cash_flow", [("2024-03-31", 11.0), ("2025-03-31", 15.0)])
    codes = {r["code"] for r in analyse_cash_quality(series, coverage_pct=90)}
    assert "strong_cash_conversion" in codes


def test_evidence_required_no_hallucination():
    assert make_relationship(
        category="X",
        relationship="A vs B",
        observation="invented",
        narrative="invented",
        evidence=[],
        confidence="High",
        severity="High",
        code="fake",
    ) is None

    pack = build_driver_pack("TCS", series_map=_base_map())
    assert pack["fire_01_unchanged"] is True
    for r in pack["relationships"]:
        assert r.get("evidence")
        assert r.get("confidence") in {"High", "Medium", "Low"}
        assert "BUY" not in (r.get("narrative") or "").upper()
        assert "SELL" not in (r.get("narrative") or "").upper()


def test_false_positive_prevention_insufficient_history():
    thin = {"revenue": _pts("revenue", [("2025-03-31", 100.0)])}
    pack = build_driver_pack("X", series_map=thin)
    # No multi-period relationships without aligned history
    assert pack["n_relationships"] == 0


def test_cross_statement_consistency_pack():
    pack = drivers("TCS", series_map=_base_map())
    assert pack["ok"] is True
    assert pack["section"] == "financial_drivers"
    assert "subsections" in pack
    assert "cash_flow_drivers" in pack["subsections"]
    assert pack["mission_control"]["relationship_findings"] == pack["n_relationships"]
    rel = relationships("TCS", series_map=_base_map())
    assert rel["n"] == pack["n_relationships"]


def test_api_facades_and_fire01_regression():
    # FIRE-01 company shape unchanged (no drivers key forced)
    c1 = fire01_company("ZZZZNOPE")
    assert "findings" in c1
    assert "executive_summary" in c1
    assert c1.get("buy_sell") is False

    # FIRE-01 report sections unchanged when built with injected empty-ish series
    series = {
        "revenue": _pts("revenue", [("2024-03-31", 100.0), ("2025-03-31", 110.0)]),
        "operating_margin": _pts("operating_margin", [("2024-03-31", 10.0), ("2025-03-31", 11.0)]),
    }
    r1 = build_report("TCS", series_map=series)
    assert "financial_drivers" not in r1["sections"]  # FIRE-01 sections untouched
    assert r1["buy_sell"] is False

    d = financial_drivers("TCS")
    assert d["workstream_id"] == WORKSTREAM_ID or d.get("ok") is True
    # empty warehouse still ok
    assert "relationships" in d or d.get("enabled") is False

    rel = financial_relationships("TCS")
    assert "relationships" in rel


def test_confidence_downgrade_conflict_path():
    from financial_intelligence.drivers.core import confidence_for_points

    pts = [{"validation_status": "APPROVED"}]
    highish = confidence_for_points(pts, history_n=8, coverage_pct=90, conflict=False)
    lower = confidence_for_points(pts, history_n=8, coverage_pct=90, conflict=True)
    order = ["High", "Medium", "Low"]
    assert order.index(lower) >= order.index(highish)
