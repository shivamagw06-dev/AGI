"""FSE-05 — Validation & Financial Quality Engine tests."""

from __future__ import annotations

import copy
import json

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.parsing.production import parse_bytes
from financial_statements_engine.store import store_root
from financial_statements_engine.validation.accounting.rules import run as accounting_run
from financial_statements_engine.validation.approval.decision import decide
from financial_statements_engine.validation.pipeline import validate_draft
from financial_statements_engine.validation.production import dashboard, health
from financial_statements_engine.validation.schema import WORKSTREAM_ID
from financial_statements_engine.validation.statistical.rules import run as statistical_run


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _rich_pack() -> bytes:
    return json.dumps(
        {
            "fields": {
                "Revenue From Operations": {"value": 100.0, "unit_scale": "crores"},
                "PAT": {"value": 20.0, "unit_scale": "crores"},
                "PBT": {"value": 28.0, "unit_scale": "crores"},
                "TaxExpense": {"value": 8.0, "unit_scale": "crores"},
                "Finance Costs": {"value": 2.0, "unit_scale": "crores"},
                "CashAndCashEquivalents": {"value": 30.0, "unit_scale": "crores"},
                "TotalAssets": {"value": 200.0, "unit_scale": "crores"},
                "TotalEquity": {"value": 120.0, "unit_scale": "crores"},
                "TotalLiabilities": {"value": 80.0, "unit_scale": "crores"},
                "CurrentAssets": {"value": 90.0, "unit_scale": "crores"},
                "NonCurrentAssets": {"value": 110.0, "unit_scale": "crores"},
                "CurrentLiabilities": {"value": 40.0, "unit_scale": "crores"},
                "NonCurrentLiabilities": {"value": 40.0, "unit_scale": "crores"},
                "NetCashFlowsFromUsedInOperatingActivities": {"value": 25.0, "unit_scale": "crores"},
                "CashFlowsFromUsedInInvestingActivities": {"value": -10.0, "unit_scale": "crores"},
                "CashFlowsFromUsedInFinancingActivities": {"value": -5.0, "unit_scale": "crores"},
                "IncreaseDecreaseInCashAndCashEquivalents": {"value": 10.0, "unit_scale": "crores"},
            }
        },
        sort_keys=True,
    ).encode("utf-8")


def test_vfqe_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["never_reads_raw_evidence"] is True
    assert h["never_edits_drafts"] is True
    assert h["never_reparses"] is True
    assert h["issues_recommendations"] is False


def test_validate_draft_never_mutates_and_publishes(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:vfqe1",
    )
    assert draft["ok"]
    before = copy.deepcopy(draft)
    result = validate_draft(draft)
    assert draft == before
    assert result["draft_mutated"] is False
    assert result["reparses_documents"] is False
    assert result["approval"]["publishable"] is True
    assert result["approval"]["approval_status"] in ("APPROVED", "APPROVED_WITH_WARNINGS")
    assert result["writes_warehouse"] is True
    assert result["quality_score"]["explainable"] is True
    assert result["report"]["mutates_draft"] is False
    pub = store_root() / "published" / "TCS" / "latest_validated.json"
    assert pub.exists()
    events = {e["event_type"] for e in get_bus().tail(100)}
    assert "validation.completed.v1" in events
    assert "validation.approved.v1" in events


def test_incomplete_input_quarantined(fse_tmp):
    result = validate_draft({"ok": True, "ticker": "TCS", "draft_id": "draft:x"})
    assert result["approval"]["approval_status"] == "QUARANTINED"
    assert result["writes_warehouse"] is False
    assert result["quarantine_result"]["quarantined"] is True


def test_accounting_identity_failure_rejects(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:vfqe_acct",
    )
    # Break BS identity in mapped metrics (do not simulate inventing — test validator reaction)
    draft = copy.deepcopy(draft)
    draft["mapped"]["metrics"]["total_assets"]["normalized_value"] = 9999.0
    draft["mapped"]["metrics"]["total_assets"]["reported_value"] = 9999.0
    findings = accounting_run(draft)
    bs = next(f for f in findings if f["rule_id"] == "ACCT_BS_IDENTITY")
    assert bs["status"] == "FAIL"
    decision = decide(findings)
    assert decision["approval_status"] == "REJECTED"
    result = validate_draft(draft)
    assert result["approval"]["approval_status"] == "REJECTED"
    assert result["writes_warehouse"] is False


def test_statistical_warning_does_not_auto_fail(fse_tmp):
    draft = {
        "ok": True,
        "draft_id": "draft:stat",
        "manifest_id": "pm:stat",
        "coverage_matrix_id": "ecm:stat",
        "document_hash": "abc",
        "ticker": "TCS",
        "evidence_id": "e:stat",
        "period": {"period_end": "2025-03-31", "period_kind": "annual"},
        "currency": {"canonical_currency": "INR"},
        "confidence": {"overall": 0.9},
        "coverage_scorecard": {"coverage_percentage": 0.8},
        "coverage_matrix": {
            "sections": [
                {"domain": "income_statement", "status": "PARTIAL"},
                {"domain": "balance_sheet", "status": "PARTIAL"},
                {"domain": "cash_flow", "status": "PARTIAL"},
            ]
        },
        "manifest": {"schema_version": "1", "metric_registry_version": "1", "immutable": True},
        "mapped": {
            "metrics": {
                "revenue": {"reported_value": 100.0, "normalized_value": 100.0, "scale": "crores"},
                "net_income": {"reported_value": 10.0, "normalized_value": 10.0, "scale": "crores"},
                "total_assets": {"reported_value": 200.0, "normalized_value": 200.0, "scale": "crores"},
                "total_equity": {"reported_value": 120.0, "normalized_value": 120.0, "scale": "crores"},
                "operating_cash_flow": {"reported_value": 15.0, "normalized_value": 15.0, "scale": "crores"},
                "depreciation": {"reported_value": -1.0, "normalized_value": -1.0, "scale": "crores"},
            }
        },
        "duplicates": {"duplicate_flags": []},
    }
    stats = statistical_run(draft)
    neg = next(f for f in stats if f["rule_id"] == "STAT_NEG_DEP")
    assert neg["status"] == "WARN"
    assert neg["severity"] == "WARNING"
    result = validate_draft(draft)
    # warnings alone → approved with warnings (publishable)
    assert result["approval"]["approval_status"] == "APPROVED_WITH_WARNINGS"
    assert result["approval"]["publishable"] is True


def test_revalidation_new_record(fse_tmp):
    draft = parse_bytes(
        "INFY",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:reval1",
    )
    a = validate_draft(draft)
    b = validate_draft(draft)
    assert a["validation_id"] != b["validation_id"]


def test_dashboard(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:dash5",
    )
    validate_draft(draft)
    dash = dashboard()
    assert dash["reports_indexed"] >= 1
    assert "approval_rates" in dash
