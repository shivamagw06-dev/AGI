"""FIRE-04 — Evidence Fusion Engine deterministic tests."""

from __future__ import annotations

from evidence_fusion.engine import build_fusion_pack
from evidence_fusion.fusion import fuse_all
from evidence_fusion.production import alignment, company, conflicts, health, supported
from evidence_fusion.schema import (
    RESULT_INSUFFICIENT,
    RESULT_NOT_SUPPORTED,
    RESULT_PARTIAL,
    RESULT_SUPPORTED,
    WORKSTREAM_ID,
)
from evidence_fusion.signals import metric_signal


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
    fact_id: str = "bf:test",
    period: str = "FY2026",
) -> dict:
    return {
        "fact_id": fact_id,
        "category": category,
        "statement": statement,
        "evidence": statement,
        "page": 47,
        "section": "STRATEGY",
        "document": "Annual Report FY2026",
        "document_type": "ANNUAL_REPORT",
        "reporting_period": period,
        "confidence": "High",
    }


def _series_supported_capacity_debt_margins() -> dict:
    return {
        "capex": _pts("capex", [("2025-03-31", 100.0), ("2026-03-31", 142.0)]),
        "operating_cash_flow": _pts("operating_cash_flow", [("2025-03-31", 80.0), ("2026-03-31", 95.0)]),
        "free_cash_flow": _pts("free_cash_flow", [("2025-03-31", 50.0), ("2026-03-31", 60.0)]),
        "working_capital": _pts("working_capital", [("2025-03-31", 40.0), ("2026-03-31", 38.0)]),
        "total_debt": _pts("total_debt", [("2025-03-31", 200.0), ("2026-03-31", 160.0)]),
        "net_debt": _pts("net_debt", [("2025-03-31", 150.0), ("2026-03-31", 110.0)]),
        "interest_coverage": _pts("interest_coverage", [("2025-03-31", 4.0), ("2026-03-31", 5.5)]),
        "operating_margin": _pts("operating_margin", [("2025-03-31", 16.0), ("2026-03-31", 18.5)]),
        "revenue": _pts("revenue", [("2025-03-31", 1000.0), ("2026-03-31", 1120.0)]),
        "dividends": _pts("dividends", [("2025-03-31", 10.0), ("2026-03-31", 12.0)]),
        "cash": _pts("cash", [("2025-03-31", 50.0), ("2026-03-31", 55.0)]),
    }


def _series_unsupported_cash_margins() -> dict:
    return {
        "operating_cash_flow": _pts("operating_cash_flow", [("2025-03-31", 90.0), ("2026-03-31", 70.0)]),
        "free_cash_flow": _pts("free_cash_flow", [("2025-03-31", 40.0), ("2026-03-31", 25.0)]),
        "working_capital": _pts("working_capital", [("2025-03-31", 30.0), ("2026-03-31", 48.0)]),
        "operating_margin": _pts("operating_margin", [("2025-03-31", 18.0), ("2026-03-31", 15.0)]),
        "capex": _pts("capex", [("2025-03-31", 100.0), ("2026-03-31", 80.0)]),
        "total_debt": _pts("total_debt", [("2025-03-31", 100.0), ("2026-03-31", 140.0)]),
        "revenue": _pts("revenue", [("2025-03-31", 1000.0), ("2026-03-31", 980.0)]),
    }


def test_fire04_health():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["uses_llm"] is False
    assert h["buy_sell"] is False
    assert h["never_mutates_warehouse"] is True
    assert h["fire_01_unchanged"] is True
    assert h["fire_02_unchanged"] is True
    assert h["fire_03_unchanged"] is True


def test_metric_signal_direction():
    sig = metric_signal(_pts("capex", [("2025-03-31", 100.0), ("2026-03-31", 142.0)]))
    assert sig is not None
    assert sig["direction"] == "up"
    assert sig["pct_change"] is not None and sig["pct_change"] > 40


def test_management_strategy_supported_capacity():
    facts = [_fact("Capacity Expansion", "We are expanding manufacturing capacity.", fact_id="bf:cap")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_supported_capacity_debt_margins(), coverage_pct=90)
    assert any(r["fusion_result"] == RESULT_SUPPORTED and r["topic_id"] == "capacity_expansion" for r in rows)
    hit = next(r for r in rows if r["topic_id"] == "capacity_expansion")
    assert "capex" in hit["supporting_metrics"]
    assert hit["evidence_ids"]
    assert hit["page"] == 47


def test_management_strategy_unsupported_cash():
    facts = [_fact("Growth Strategy", "We are improving cash generation.", fact_id="bf:cash")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_unsupported_cash_margins(), coverage_pct=85)
    hit = next(r for r in rows if r["topic_id"] == "cash_generation")
    assert hit["fusion_result"] == RESULT_NOT_SUPPORTED
    assert "not supported" in hit["narrative"].lower()


def test_cash_generation_consistency_supported():
    facts = [_fact("Cash Deployment", "Improving cash generation remains a focus.", fact_id="bf:cash2")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_supported_capacity_debt_margins(), coverage_pct=90)
    hit = next(r for r in rows if r["topic_id"] == "cash_generation")
    assert hit["fusion_result"] == RESULT_SUPPORTED


def test_debt_reduction_consistency():
    facts = [_fact("Debt Reduction", "Debt reduction remains a priority.", fact_id="bf:debt")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_supported_capacity_debt_margins(), coverage_pct=90)
    hit = next(r for r in rows if r["topic_id"] == "debt_reduction")
    assert hit["fusion_result"] == RESULT_SUPPORTED
    assert "net_debt" in hit["supporting_metrics"] or "total_debt" in hit["supporting_metrics"]


def test_margin_consistency_unsupported():
    facts = [_fact("Cost Optimisation", "Margin improvement initiatives underway.", fact_id="bf:mgn")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_unsupported_cash_margins(), coverage_pct=80)
    hit = next(r for r in rows if r["topic_id"] == "margin_improvement")
    assert hit["fusion_result"] == RESULT_NOT_SUPPORTED


def test_risk_consistency():
    facts = [
        _fact(
            "Risk",
            "Disclosed risk: Interest rates and leverage.",
            fact_id="bf:risk",
        )
    ]
    # Rising debt → risk disclosure aligns (Supported in risk_alignment_mode)
    series = {
        "total_debt": _pts("total_debt", [("2025-03-31", 100.0), ("2026-03-31", 140.0)]),
        "interest_coverage": _pts("interest_coverage", [("2025-03-31", 6.0), ("2026-03-31", 3.5)]),
    }
    rows = fuse_all(fire03_facts=facts, series_map=series, coverage_pct=70)
    hit = next(r for r in rows if r["topic_id"] == "risk_leverage")
    assert hit["fusion_result"] in {RESULT_SUPPORTED, RESULT_PARTIAL}


def test_capital_allocation_consistency():
    facts = [_fact("Dividends", "Dividend policy and shareholder returns described.", fact_id="bf:div")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_supported_capacity_debt_margins(), coverage_pct=90)
    hit = next(r for r in rows if r["topic_id"] == "capital_returns")
    assert hit["fusion_result"] == RESULT_SUPPORTED


def test_missing_evidence_product_launch():
    facts = [_fact("Product Launches", "Product launch in high-performance adhesives.", fact_id="bf:pl")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_supported_capacity_debt_margins(), coverage_pct=90)
    hit = next(r for r in rows if r["topic_id"] == "product_launch")
    assert hit["fusion_result"] == RESULT_INSUFFICIENT


def test_evidence_confidence_uses_fkb_modifiers():
    facts = [_fact("Capacity Expansion", "Capacity expansion is underway.", fact_id="bf:c2")]
    rows = fuse_all(fire03_facts=facts, series_map=_series_supported_capacity_debt_margins(), coverage_pct=95)
    hit = next(r for r in rows if r["topic_id"] == "capacity_expansion")
    assert hit["confidence"] in {"High", "Medium", "Low"}
    assert hit.get("confidence_detail", {}).get("applied_modifiers") is not None


def test_pack_and_api_surfaces():
    facts = [
        _fact("Capacity Expansion", "We are expanding manufacturing capacity.", fact_id="bf:1"),
        _fact("Debt Reduction", "Debt reduction remains a priority.", fact_id="bf:2"),
        _fact("Product Launches", "New product launch planned.", fact_id="bf:3"),
        _fact("Cost Optimisation", "Margin improvement initiatives.", fact_id="bf:4"),
    ]
    series = {
        **_series_supported_capacity_debt_margins(),
        "operating_margin": _pts("operating_margin", [("2025-03-31", 18.0), ("2026-03-31", 15.0)]),
    }
    pack = build_fusion_pack(
        "DEMO",
        series_map=series,
        fire03_facts=facts,
        fire01_findings=[],
        fire02_relationships=[],
        coverage_pct=90,
    )
    assert pack["ok"] is True
    assert pack["n_findings"] >= 3
    assert pack["alignment"]["evidence_alignment_score"] is not None
    assert "supported_findings" in pack["mission_control"]

    c = company(
        "DEMO",
        series_map=series,
        fire03_facts=facts,
        fire01_findings=[],
        fire02_relationships=[],
        coverage_pct=90,
    )
    assert c["report_type"] == "EvidenceFusionReport" or c.get("sections")
    assert supported(
        "DEMO",
        series_map=series,
        fire03_facts=facts,
        fire01_findings=[],
        fire02_relationships=[],
        coverage_pct=90,
    )["n"] >= 1
    assert conflicts(
        "DEMO",
        series_map=series,
        fire03_facts=facts,
        fire01_findings=[],
        fire02_relationships=[],
        coverage_pct=90,
    )["n"] >= 1
    a = alignment(
        "DEMO",
        series_map=series,
        fire03_facts=facts,
        fire01_findings=[],
        fire02_relationships=[],
        coverage_pct=90,
    )
    assert a["alignment"]["total_findings"] >= 1


def test_regression_fire01_fire02_fire03_unchanged():
    from business_intelligence.production import health as fire03_health
    from financial_intelligence.drivers.production import health as fire02_health
    from financial_intelligence.production import health as fire01_health

    assert fire01_health()["workstream_id"] == "FIRE-01"
    assert fire02_health()["workstream_id"] == "FIRE-02"
    assert fire02_health()["fire_01_unchanged"] is True
    assert fire03_health()["workstream_id"] == "FIRE-03"
    assert fire03_health()["fire_01_unchanged"] is True
    assert fire03_health()["fire_02_unchanged"] is True

    h4 = health()
    assert h4["workstream_id"] == "FIRE-04"
    assert h4["fire_01_unchanged"] is True
    assert h4["fire_02_unchanged"] is True
    assert h4["fire_03_unchanged"] is True
