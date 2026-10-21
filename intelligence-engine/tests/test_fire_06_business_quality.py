"""FIRE-06 — Business Quality Engine deterministic tests."""

from __future__ import annotations

from business_quality.engine import build_quality_pack
from business_quality.production import company, health, pillars, quality
from business_quality.schema import (
    PILLAR_BALANCE,
    PILLAR_CASH,
    PILLAR_EXECUTION,
    PILLAR_GROWTH,
    PILLAR_MODEL,
    PILLAR_PROFIT,
    WORKSTREAM_ID,
)
from business_quality.scoring import derive_overall
from business_quality.weights import load_pillar_weights
from financial_knowledge import knowledge


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


def _strong_series() -> dict:
    return {
        "revenue": _pts("revenue", [("2024-03-31", 100.0), ("2025-03-31", 112.0), ("2026-03-31", 125.0)]),
        "operating_margin": _pts("operating_margin", [("2024-03-31", 14.0), ("2025-03-31", 15.5), ("2026-03-31", 17.0)]),
        "gross_margin": _pts("gross_margin", [("2024-03-31", 40.0), ("2025-03-31", 41.0), ("2026-03-31", 42.0)]),
        "net_margin": _pts("net_margin", [("2024-03-31", 10.0), ("2025-03-31", 11.0), ("2026-03-31", 12.0)]),
        "roe": _pts("roe", [("2024-03-31", 12.0), ("2025-03-31", 13.0), ("2026-03-31", 14.0)]),
        "roce": _pts("roce", [("2024-03-31", 11.0), ("2025-03-31", 12.0), ("2026-03-31", 13.0)]),
        "operating_cash_flow": _pts("operating_cash_flow", [("2024-03-31", 20.0), ("2025-03-31", 24.0), ("2026-03-31", 28.0)]),
        "free_cash_flow": _pts("free_cash_flow", [("2024-03-31", 12.0), ("2025-03-31", 14.0), ("2026-03-31", 16.0)]),
        "working_capital": _pts("working_capital", [("2024-03-31", 30.0), ("2025-03-31", 29.0), ("2026-03-31", 28.0)]),
        "net_income": _pts("net_income", [("2024-03-31", 10.0), ("2025-03-31", 12.0), ("2026-03-31", 14.0)]),
        "net_debt": _pts("net_debt", [("2024-03-31", 80.0), ("2025-03-31", 70.0), ("2026-03-31", 55.0)]),
        "interest_coverage": _pts("interest_coverage", [("2024-03-31", 4.0), ("2025-03-31", 5.0), ("2026-03-31", 6.0)]),
        "cash": _pts("cash", [("2024-03-31", 20.0), ("2025-03-31", 25.0), ("2026-03-31", 30.0)]),
        "capex": _pts("capex", [("2024-03-31", 8.0), ("2025-03-31", 9.0), ("2026-03-31", 10.0)]),
        "dividends": _pts("dividends", [("2024-03-31", 2.0), ("2025-03-31", 2.5), ("2026-03-31", 3.0)]),
    }


def _facts() -> list[dict]:
    return [
        {
            "fact_id": "bf:seg",
            "category": "Business Segments",
            "statement": "Segment / vertical: Specialty Chemicals",
            "evidence": "Specialty Chemicals",
            "page": 10,
            "section": "BUSINESS_SEGMENTS",
            "document": "AR FY2026",
            "reporting_period": "FY2026",
            "confidence": "High",
        },
        {
            "fact_id": "bf:geo",
            "category": "Geographic Exposure",
            "statement": "Geographic market referenced",
            "evidence": "India, North America, Europe",
            "page": 11,
            "section": "OTHER",
            "document": "AR FY2026",
            "reporting_period": "FY2026",
            "confidence": "High",
        },
        {
            "fact_id": "bf:rec",
            "category": "Revenue Model",
            "statement": "Recurring / subscription revenue referenced",
            "evidence": "recurring maintenance contracts",
            "page": 12,
            "section": "OTHER",
            "document": "AR FY2026",
            "reporting_period": "FY2026",
            "confidence": "Medium",
        },
    ]


def test_fire06_health():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["uses_llm"] is False
    assert h["buy_sell"] is False
    assert h["valuation"] is False
    assert h["pillar_scores_primary"] is True
    assert h["fire_05_unchanged"] is True


def test_fkb_quality_weights():
    rows = knowledge.list_quality_weights()
    assert len(rows) == 7
    assert abs(sum(float(r["weight"]) for r in rows) - 1.0) < 1e-6
    w = load_pillar_weights()
    assert w["hardcoded_magic_numbers"] is False
    assert "growth_quality" in w["weights"]


def test_growth_quality():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=_facts(),
        fire04_findings=[],
        fire05_score={"management_execution_score": 70.0, "objectives_tracked": 3, "delivered": 2, "outstanding": 1},
        fire05_findings=[],
        coverage_pct=90,
    )
    g = pack["pillars"][PILLAR_GROWTH]
    assert g["score"] is not None
    assert g["score"] >= 50
    assert g["evidence"]


def test_profitability_quality():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=[],
        fire04_findings=[],
        fire05_score=None,
        fire05_findings=[],
        coverage_pct=85,
    )
    p = pack["pillars"][PILLAR_PROFIT]
    assert p["score"] is not None
    assert p["score"] > 50


def test_cash_quality():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=[],
        fire04_findings=[],
        fire05_score=None,
        fire05_findings=[],
        coverage_pct=85,
    )
    c = pack["pillars"][PILLAR_CASH]
    assert c["score"] is not None
    assert any(e.get("metric") in {"operating_cash_flow", "free_cash_flow", "cash_conversion_ocf_pat"} for e in c["evidence"])


def test_balance_sheet_quality():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=[],
        fire04_findings=[],
        fire05_score=None,
        fire05_findings=[],
        coverage_pct=85,
    )
    b = pack["pillars"][PILLAR_BALANCE]
    assert b["score"] is not None
    assert b["score"] > 50


def test_capital_allocation_quality():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=[
            {
                "fact_id": "bf:div",
                "category": "Dividends",
                "statement": "Dividend commentary disclosed",
                "evidence": "dividends",
                "page": 20,
                "section": "CAPITAL_ALLOCATION",
                "document": "AR",
                "reporting_period": "FY2026",
                "confidence": "High",
            }
        ],
        fire04_findings=[
            {
                "topic_id": "debt_reduction",
                "fusion_result": "Supported",
                "consistency_bucket": "capital_allocation_consistency",
            }
        ],
        fire05_score=None,
        fire05_findings=[],
        coverage_pct=80,
    )
    assert pack["pillars"]["capital_allocation_quality"]["score"] is not None


def test_business_model_stability():
    pack = build_quality_pack(
        "DEMO",
        series_map={"revenue": _pts("revenue", [("2025-03-31", 100.0), ("2026-03-31", 110.0)])},
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=_facts(),
        fire04_findings=[],
        fire05_score=None,
        fire05_findings=[],
        coverage_pct=70,
    )
    m = pack["pillars"][PILLAR_MODEL]
    assert m["score"] is not None
    assert any(e.get("theme") == "segment_diversification" for e in m["evidence"])


def test_execution_reuses_fire05():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=[],
        fire04_findings=[],
        fire05_score={"management_execution_score": 72.5, "objectives_tracked": 4, "delivered": 3, "outstanding": 1},
        fire05_findings=[{"objective_id": "DEBT_REDUCTION_FY2025_001", "current_status": "Delivered"}],
        coverage_pct=90,
    )
    ex = pack["pillars"][PILLAR_EXECUTION]
    assert ex["score"] == 72.5
    assert ex["components"]["reused_fire05"] is True
    assert ex["components"]["duplicated_logic"] is False


def test_score_calculation_pillar_primary():
    pillars_map = {
        "growth_quality": {"score": 80.0},
        "profitability_quality": {"score": 70.0},
        "cash_flow_quality": {"score": 60.0},
        "balance_sheet_quality": {"score": 50.0},
        "capital_allocation_quality": {"score": 40.0},
        "management_execution": {"score": 90.0},
        "business_model_stability": {"score": 55.0},
    }
    overall = derive_overall(pillars_map)
    assert overall["pillars_primary"] is True
    assert overall["overall_score"] is not None
    assert overall["hardcoded_magic_numbers"] is False
    # Missing pillar renormalizes
    partial = {k: v for k, v in pillars_map.items() if k != "business_model_stability"}
    o2 = derive_overall(partial)
    assert o2["renormalized"] is True
    assert "business_model_stability" in o2["pillars_skipped"]


def test_confidence_and_language_guard():
    pack = build_quality_pack(
        "DEMO",
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=_facts(),
        fire04_findings=[],
        fire05_score={"management_execution_score": 66.0, "objectives_tracked": 2, "delivered": 1, "outstanding": 1},
        fire05_findings=[],
        coverage_pct=92,
    )
    assert pack["language_guard_violations"] == []
    assert pack["confidence"]["pillars_scored"] >= 5
    for f in pack["findings"]:
        assert f.get("confidence") in {"High", "Medium", "Low"}
        low = (f.get("narrative") or "").lower()
        assert "excellent company" not in low
        assert "great investment" not in low


def test_api_surfaces():
    kwargs = dict(
        series_map=_strong_series(),
        fire01_findings=[],
        fire02_relationships=[],
        fire03_facts=_facts(),
        fire04_findings=[],
        fire05_score={"management_execution_score": 60.0, "objectives_tracked": 2, "delivered": 1, "outstanding": 1},
        fire05_findings=[],
        coverage_pct=88,
    )
    c = company("DEMO", **kwargs)
    assert c["ok"] is True
    assert c["pillar_scores_primary"] is True
    assert c["quality_score"] is not None
    q = quality("DEMO", **kwargs)
    assert q["quality_score"] == c["quality_score"]
    p = pillars("DEMO", **kwargs)
    assert p["n"] == 7
    assert c["mission_control"]["quality_score"] is not None


def test_regression_fire01_to_fire05_unchanged():
    from business_intelligence.production import health as h3
    from evidence_fusion.production import health as h4
    from financial_intelligence.drivers.production import health as h2
    from financial_intelligence.production import health as h1
    from management_execution.production import health as h5

    assert h1()["workstream_id"] == "FIRE-01"
    assert h2()["workstream_id"] == "FIRE-02"
    assert h3()["workstream_id"] == "FIRE-03"
    assert h4()["workstream_id"] == "FIRE-04"
    assert h5()["workstream_id"] == "FIRE-05"
    h6 = health()
    assert h6["workstream_id"] == "FIRE-06"
    for key in ("fire_01_unchanged", "fire_02_unchanged", "fire_03_unchanged", "fire_04_unchanged", "fire_05_unchanged"):
        assert h6[key] is True
