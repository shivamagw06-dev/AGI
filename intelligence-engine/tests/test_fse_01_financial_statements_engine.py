"""FSE-01 — Financial Statements Engine M0/M1 contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financial_statements_engine.canonical import build_statement
from financial_statements_engine.normalize import normalize_fields
from financial_statements_engine.production import get_statements, health, ingest_and_publish
from financial_statements_engine.registry import assert_unique_canonical, resolve, registry_manifest
from financial_statements_engine.validate import validate_statement
from financial_statements_engine.warehouse import publish_statement


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    return tmp_path / "fse"


def test_health_contract():
    h = health()
    assert h["status"] == "ok"
    assert h["workstream_id"] == "FSE-01"
    assert h["engine"] == "financial_statements_engine"
    assert h["issues_recommendations"] is False
    assert h["modifies_decision_engine"] is False
    assert "raw_evidence" in h["layers"]
    assert "recommendation" not in h
    assert h["recommendation_policy"] == "financial_warehouse_only_no_buy_sell"


def test_registry_unique_and_revenue_synonym():
    assert_unique_canonical()
    assert resolve("revenue_from_operations") == "revenue"
    assert resolve("RevenueFromOperations") == "revenue"
    assert resolve("revenue") == "revenue"
    assert resolve("pat") == "net_income"
    m = registry_manifest()
    assert m["authority"] == "metric_registry"
    assert m["canonical_count"] >= len(set(m["income"] + m["balance_sheet"] + m["cash_flow"]))
    assert len(m["income"] + m["balance_sheet"] + m["cash_flow"]) == len(
        set(m["income"] + m["balance_sheet"] + m["cash_flow"])
    )


def test_normalize_maps_legacy_keys():
    out = normalize_fields(
        {
            "revenue_from_operations": {"value": 100.0, "unit_scale": "crores"},
            "MysteryLine": {"value": 1.0, "unit_scale": "crores"},
        }
    )
    assert "revenue" in out["metrics"]
    assert out["metrics"]["revenue"]["value_inr"] == 100.0 * 10_000_000.0
    assert "MysteryLine" in out["unmapped"]


def test_trace_evidence_blocks_publish(fse_tmp):
    stmt = build_statement(
        ticker="TCS",
        statement_type="income_statement",
        period_type="annual",
        period_end="2025-03-31",
        metrics={"revenue": {"value_inr": 1.0, "reported_value": 1.0, "unit_scale": "ones"}},
        evidence_id=None,
    )
    # strip evidence
    stmt["metrics"]["revenue"].pop("evidence_id", None)
    report = validate_statement(stmt)
    assert report["validation_status"] == "failed"
    assert any(i["code"] == "TRACE_EVIDENCE" for i in report["issues"])
    pub = publish_statement(stmt, allow_flagged=True)
    assert pub["published"] is False
    assert pub["publication_status"] == "withheld"


def test_version_preserves_history(fse_tmp):
    def _stmt(rev: float):
        return build_statement(
            ticker="TCS",
            statement_type="income_statement",
            period_type="annual",
            period_end="2025-03-31",
            metrics={
                "revenue": {
                    "value_inr": rev,
                    "reported_value": rev,
                    "unit_scale": "ones",
                    "evidence_id": "sha256:abc",
                },
                "net_income": {
                    "value_inr": rev / 10,
                    "reported_value": rev / 10,
                    "unit_scale": "ones",
                    "evidence_id": "sha256:abc",
                },
            },
            evidence_id="sha256:abc",
        )

    r1 = publish_statement(_stmt(100.0))
    r2 = publish_statement(_stmt(110.0))
    assert r1["published"] and r2["published"]
    assert r2["statement"]["version"] == r1["statement"]["version"] + 1
    assert r2["statement"]["restatement"] is True
    versions = Path(fse_tmp) / "versions" / "TCS" / "income_statement" / "2025-03-31"
    assert (versions / "v1.json").exists()
    assert (versions / "v2.json").exists()


def test_ingest_fixture_pack_idempotent_publish(fse_tmp):
    pack = {
        "quarters": [
            {
                "period_end": "2025-03-31",
                "period_type": "quarterly",
                "fiscal_year": 2025,
                "fiscal_period": "Q4",
                "confidence": 0.9,
                "income_statement": {
                    "revenue_from_operations": 64054.0,
                    "pat": 12000.0,
                    "pbt": 16000.0,
                    "tax_expense": 4000.0,
                },
                "balance_sheet": {"total_assets": 100000.0, "total_equity": 50000.0, "total_liabilities": 50000.0},
                "cash_flow": {
                    "operating_cash_flow": 15000.0,
                    "investing_cash_flow": -5000.0,
                    "financing_cash_flow": -2000.0,
                    "net_change_in_cash": 8000.0,
                },
                "source_refs": [{"evidence_id": "sha256:fixture1"}],
            }
        ]
    }
    a = ingest_and_publish("TCS", pack=pack, publish=True)
    b = ingest_and_publish("TCS", pack=pack, publish=True)
    assert a["ok"] and b["ok"]
    got = get_statements("TCS")
    assert got["ok"] is True
    assert got["published"] is not None
    # latest pointers exist; versions grow but published statement types remain unique per period
    types = {(s["statement_type"], s["period_end"]) for s in got["published"]["statements"]}
    assert ("income_statement", "2025-03-31") in types
