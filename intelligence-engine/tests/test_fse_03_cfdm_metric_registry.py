"""FSE-03 — Canonical Financial Data Model & Metric Registry tests."""

from __future__ import annotations

import pytest

from financial_statements_engine.cfdm import build_company, build_fact, build_period, health as cfdm_health
from financial_statements_engine.metric_registry.dictionary import APPENDIX_A_METRICS, CANONICAL_METRICS
from financial_statements_engine.metric_registry.production import health as registry_health
from financial_statements_engine.metric_registry.service import assert_canonical, resolve
from financial_statements_engine import registry as legacy_registry


def test_cfdm_and_registry_health():
    h = cfdm_health()
    assert h["status"] == "ok"
    assert h["workstream_id"] == "FSE-03"
    assert h["consumer_may_define_schema"] is False
    assert "company" in h["canonical_objects"]
    assert h["issues_recommendations"] is False
    rh = registry_health()
    assert rh["registry_version"].startswith("cfdm-metric-registry-")
    assert rh["manifest"]["appendix_a_count"] == len(APPENDIX_A_METRICS)


def test_appendix_a_unique_and_present():
    assert len(APPENDIX_A_METRICS) == len(set(APPENDIX_A_METRICS))
    for m in APPENDIX_A_METRICS:
        assert m in CANONICAL_METRICS
        assert CANONICAL_METRICS[m]["appendix_a"] is True
        assert CANONICAL_METRICS[m]["status"] == "active"


def test_synonyms_revenue_and_pat():
    assert resolve("Revenue From Operations") == "revenue"
    assert resolve("revenue_from_operations") == "revenue"
    assert resolve("PAT") == "net_income"
    assert resolve("pat") == "net_income"
    assert resolve("Net Profit") == "net_income"
    assert resolve("finance_costs") == "finance_cost"
    assert resolve("net_change_in_cash") == "net_cash_change"


def test_assert_canonical_rejects_unknown():
    assert_canonical("revenue")
    with pytest.raises(Exception):
        assert_canonical("totally_made_up_metric_xyz")


def test_build_fact_requires_evidence_for_publish():
    company = build_company(exchange="NSE", ticker="RELIANCE", isin="INE002A01018")
    period = build_period(
        company_id=company["company_id"],
        period_end="2025-03-31",
        period_kind="annual",
        consolidation_type="consolidated",
    )
    with pytest.raises(ValueError, match="published_fact_requires_evidence"):
        build_fact(
            company_id=company["company_id"],
            period_id=period["period_id"],
            statement_type="income_statement",
            metric="revenue",
            reported_value=267000,
            scale="crores",
            source="nse_xbrl",
            status="published",
        )
    fact = build_fact(
        company_id=company["company_id"],
        period_id=period["period_id"],
        statement_type="income_statement",
        metric="revenue",
        reported_value=267000,
        scale="crores",
        source="nse_xbrl",
        evidence_id="sha256:abc",
        status="published",
        confidence=0.9,
    )
    assert fact["metric"] == "revenue"
    assert fact["normalized_value"] == 267000 * 10_000_000.0
    assert fact["evidence"]["evidence_id"] == "sha256:abc"


def test_build_fact_rejects_non_canonical_metric():
    company = build_company(exchange="NSE", ticker="TCS")
    period = build_period(
        company_id=company["company_id"],
        period_end="2025-03-31",
        period_kind="annual",
        consolidation_type="standalone",
    )
    with pytest.raises(ValueError, match="non_canonical_metric"):
        build_fact(
            company_id=company["company_id"],
            period_id=period["period_id"],
            statement_type="income_statement",
            metric="Revenue From Operations",  # synonym, not canonical warehouse id
            reported_value=1,
            source="nse_xbrl",
            evidence_id="sha256:x",
            status="draft",
        )


def test_standalone_vs_consolidated_period_ids_differ():
    company = build_company(exchange="NSE", ticker="TCS", isin="INE467B01029")
    a = build_period(
        company_id=company["company_id"],
        period_end="2025-03-31",
        period_kind="annual",
        consolidation_type="standalone",
    )
    b = build_period(
        company_id=company["company_id"],
        period_end="2025-03-31",
        period_kind="annual",
        consolidation_type="consolidated",
    )
    assert a["period_id"] != b["period_id"]
    assert ":standalone" in a["period_id"]
    assert ":consolidated" in b["period_id"]


def test_legacy_registry_facade_matches_service():
    assert legacy_registry.resolve("pat") == resolve("pat") == "net_income"
    assert legacy_registry.resolve("revenue_from_operations") == "revenue"
    m = legacy_registry.registry_manifest()
    assert m["authority"] == "metric_registry"
    assert m["canonical_count"] == len(CANONICAL_METRICS)
