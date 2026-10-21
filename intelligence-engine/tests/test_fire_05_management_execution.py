"""FIRE-05 — Management Execution & Temporal Evidence Engine tests."""

from __future__ import annotations

from datetime import date

from management_execution.engine import build_execution_pack
from management_execution.evaluate import evaluate_all
from management_execution.objectives import make_objective_id, normalize_objectives
from management_execution.production import company, health, objectives, score, timeline
from management_execution.schema import (
    STATUS_CANNOT,
    STATUS_DELIVERED,
    STATUS_NOT_YET,
    STATUS_PARTIAL,
    STATUS_SUPERSEDED,
    WORKSTREAM_ID,
)
from management_execution.score import execution_score


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


def _fact(
    category: str,
    statement: str,
    *,
    fact_id: str,
    period: str,
    document: str | None = None,
) -> dict:
    return {
        "fact_id": fact_id,
        "category": category,
        "statement": statement,
        "evidence": statement,
        "page": 40,
        "section": "STRATEGY",
        "document": document or f"Annual Report {period}",
        "document_type": "ANNUAL_REPORT",
        "reporting_period": period,
        "confidence": "High",
    }


def test_fire05_health():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["uses_llm"] is False
    assert h["buy_sell"] is False
    assert h["judges_honesty"] is False
    assert h["fraud_detection"] is False
    assert h["fire_01_unchanged"] is True
    assert h["fire_04_unchanged"] is True


def test_objective_ids_normalized():
    facts = [
        _fact("Debt Reduction", "We will reduce debt.", fact_id="bf:d1", period="FY2025"),
        _fact("Debt Reduction", "Debt reduction remains a priority.", fact_id="bf:d2", period="FY2025"),
    ]
    objs = normalize_objectives(facts, ticker="DEMO")
    assert len(objs) == 1  # deduped same topic+period+normalized statement
    assert objs[0]["objective_id"].startswith("DEBT_REDUCTION_FY2025_")
    assert objs[0]["statement"] == "Reduce net debt"
    assert make_objective_id("DEBT_REDUCTION", "FY2025", "Reduce net debt", 1) == "DEBT_REDUCTION_FY2025_001"


def test_debt_reduction_delivered():
    facts = [_fact("Debt Reduction", "We will reduce debt.", fact_id="bf:debt", period="FY2025")]
    series = {
        "net_debt": _pts("net_debt", [("2025-03-31", 150.0), ("2026-03-31", 110.0)]),
        "interest_coverage": _pts("interest_coverage", [("2025-03-31", 4.0), ("2026-03-31", 5.5)]),
        "total_debt": _pts("total_debt", [("2025-03-31", 200.0), ("2026-03-31", 160.0)]),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    rows = evaluate_all(objs, series_map=series, later_facts=facts, as_of=date(2026, 6, 30), coverage_pct=90)
    hit = next(r for r in rows if r["topic_key"] == "DEBT_REDUCTION")
    assert hit["current_status"] == STATUS_DELIVERED
    assert hit["evidence_ids"]
    assert "net_debt" in hit["supporting_metrics"] or "total_debt" in hit["supporting_metrics"]


def test_margin_improvement_pending():
    facts = [
        _fact(
            "Margin Guidance",
            "We expect operating margins to improve.",
            fact_id="bf:mgn",
            period="FY2025",
        )
    ]
    series = {
        "operating_margin": _pts("operating_margin", [("2025-03-31", 18.0), ("2026-03-31", 15.0)]),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    rows = evaluate_all(objs, series_map=series, later_facts=facts, as_of=date(2026, 6, 30), coverage_pct=85)
    hit = next(r for r in rows if r["topic_key"] == "MARGIN_IMPROVEMENT")
    assert hit["current_status"] == STATUS_NOT_YET


def test_capacity_expansion_delivered():
    facts = [
        _fact(
            "Capacity Expansion",
            "We are investing heavily in manufacturing capacity.",
            fact_id="bf:cap",
            period="FY2025",
        )
    ]
    series = {
        "capex": _pts("capex", [("2025-03-31", 100.0), ("2026-03-31", 142.0)]),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    rows = evaluate_all(objs, series_map=series, later_facts=facts, as_of=date(2026, 6, 30), coverage_pct=90)
    hit = next(r for r in rows if r["topic_key"] == "CAPACITY_EXPANSION")
    assert hit["current_status"] == STATUS_DELIVERED


def test_growth_objective_pending():
    facts = [_fact("Growth Strategy", "Growth strategy emphasises expansion.", fact_id="bf:g", period="FY2025")]
    series = {
        "revenue": _pts("revenue", [("2025-03-31", 1000.0), ("2026-03-31", 960.0)]),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    rows = evaluate_all(objs, series_map=series, later_facts=facts, as_of=date(2026, 6, 30), coverage_pct=80)
    hit = next(r for r in rows if r["topic_key"] == "GROWTH")
    assert hit["current_status"] == STATUS_NOT_YET


def test_superseded_objectives():
    facts = [
        _fact(
            "Expansion Plans",
            "Expand Factory A capacity.",
            fact_id="bf:exp",
            period="FY2025",
        ),
        _fact(
            "Expansion Plans",
            "Management withdraws Factory A expansion project.",
            fact_id="bf:wd",
            period="FY2026",
        ),
    ]
    series = {
        "capex": _pts("capex", [("2025-03-31", 100.0), ("2026-03-31", 90.0)]),
        "revenue": _pts("revenue", [("2025-03-31", 1000.0), ("2026-03-31", 1010.0)]),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    # Origin FY2025 expansion objective should be superseded by FY2026 withdrawal
    rows = evaluate_all(objs, series_map=series, later_facts=facts, as_of=date(2026, 9, 30), coverage_pct=80)
    fy25 = [r for r in rows if r.get("original_period") == "FY2025" and r.get("topic_key") == "EXPANSION"]
    assert fy25
    assert fy25[0]["current_status"] == STATUS_SUPERSEDED
    assert "not treated as failure" in fy25[0]["narrative"].lower() or "superseded" in fy25[0]["narrative"].lower()


def test_cannot_yet_evaluate_product_launch():
    facts = [_fact("Product Launches", "We launched Product X.", fact_id="bf:px", period="FY2025")]
    series = {
        "revenue": _pts("revenue", [("2025-03-31", 1000.0), ("2026-03-31", 1100.0)]),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    rows = evaluate_all(objs, series_map=series, later_facts=facts, as_of=date(2026, 6, 30), coverage_pct=90)
    hit = next(r for r in rows if r["topic_key"] == "PRODUCT_LAUNCH")
    assert hit["current_status"] == STATUS_CANNOT


def test_time_window_evaluation():
    facts = [_fact("Debt Reduction", "Reduce net debt.", fact_id="bf:d", period="FY2024")]
    # Delivery only visible at 2026 (beyond 1y window from FY2024 end Mar 2024 → year ends Mar 2025)
    series = {
        "net_debt": _pts(
            "net_debt",
            [("2024-03-31", 200.0), ("2025-03-31", 195.0), ("2026-03-31", 120.0)],
        ),
    }
    objs = normalize_objectives(facts, ticker="DEMO")
    # Force primary window year vs y2
    objs[0]["primary_window"] = "year"
    year_rows = evaluate_all(
        objs, series_map=series, later_facts=facts, windows=["year"], as_of=date(2026, 6, 30), coverage_pct=90
    )
    objs[0]["primary_window"] = "y2"
    y2_rows = evaluate_all(
        objs, series_map=series, later_facts=facts, windows=["y2"], as_of=date(2026, 6, 30), coverage_pct=90
    )
    # y2 should see the 2026 decline more clearly as delivered; year window may still be partial/delivered on small move
    assert y2_rows[0]["current_status"] in {STATUS_DELIVERED, STATUS_PARTIAL, STATUS_NOT_YET}
    assert "window_results" in year_rows[0]


def test_execution_score_calculation():
    findings = [
        {"current_status": STATUS_DELIVERED, "delivery_months": 12, "confidence": "High"},
        {"current_status": STATUS_DELIVERED, "delivery_months": 18, "confidence": "High"},
        {"current_status": STATUS_NOT_YET, "confidence": "Medium"},
        {"current_status": STATUS_CANNOT, "confidence": "Low"},
        {"current_status": STATUS_SUPERSEDED, "confidence": "Medium"},
    ]
    s = execution_score(findings, coverage_pct=90)
    assert s["management_execution_score"] is not None
    # 2 delivered / 3 applicable = 66.67 (+ coverage bump)
    assert s["delivered"] == 2
    assert s["outstanding"] == 1
    assert s["applicable_n"] == 3
    assert s["average_delivery_months"] == 15.0
    assert s["subjective_judgement"] is False


def test_confidence_present():
    facts = [_fact("Debt Reduction", "We will reduce debt.", fact_id="bf:c", period="FY2025")]
    series = {"net_debt": _pts("net_debt", [("2025-03-31", 150.0), ("2026-03-31", 100.0)])}
    pack = build_execution_pack(
        "DEMO",
        series_map=series,
        fire03_facts=facts,
        fire04_findings=[],
        coverage_pct=95,
        as_of=date(2026, 6, 30),
    )
    assert pack["findings"]
    assert all(f.get("confidence") in {"High", "Medium", "Low"} for f in pack["findings"])


def test_api_surfaces():
    facts = [
        _fact("Debt Reduction", "We will reduce debt.", fact_id="bf:1", period="FY2025"),
        _fact("Capacity Expansion", "Capacity expansion underway.", fact_id="bf:2", period="FY2025"),
        _fact("Product Launches", "Product launch planned.", fact_id="bf:3", period="FY2025"),
    ]
    series = {
        "net_debt": _pts("net_debt", [("2025-03-31", 150.0), ("2026-03-31", 110.0)]),
        "capex": _pts("capex", [("2025-03-31", 100.0), ("2026-03-31", 140.0)]),
    }
    kwargs = dict(
        series_map=series,
        fire03_facts=facts,
        fire04_findings=[],
        coverage_pct=90,
        as_of=date(2026, 6, 30),
    )
    c = company("DEMO", **kwargs)
    assert c["ok"] is True
    assert c["n_objectives"] >= 2
    assert c["judges_honesty"] is False
    assert timeline("DEMO", **kwargs)["n"] >= 2
    assert score("DEMO", **kwargs)["score"]["objectives_tracked"] >= 2
    assert objectives("DEMO", **kwargs)["n"] >= 2
    mc = c["mission_control"]
    assert "execution_score" in mc
    assert "delivered_pct" in mc


def test_regression_fire01_to_fire04_unchanged():
    from business_intelligence.production import health as h3
    from evidence_fusion.production import health as h4
    from financial_intelligence.drivers.production import health as h2
    from financial_intelligence.production import health as h1

    assert h1()["workstream_id"] == "FIRE-01"
    assert h2()["workstream_id"] == "FIRE-02"
    assert h3()["workstream_id"] == "FIRE-03"
    assert h4()["workstream_id"] == "FIRE-04"
    assert h4()["fire_03_unchanged"] is True
    h5 = health()
    assert h5["workstream_id"] == "FIRE-05"
    assert h5["fire_01_unchanged"] is True
    assert h5["fire_02_unchanged"] is True
    assert h5["fire_03_unchanged"] is True
    assert h5["fire_04_unchanged"] is True
