"""FSE-06 — Financial Warehouse tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.financial_warehouse.production import (
    contract,
    contracts,
    dashboard,
    get_latest,
    health,
    time_travel,
)
from financial_statements_engine.financial_warehouse.publisher.publish import publish_validated_pack
from financial_statements_engine.financial_warehouse.schema import WORKSTREAM_ID
from financial_statements_engine.financial_warehouse.storage.roots import fact_path, warehouse_root
from financial_statements_engine.parsing.production import parse_bytes
from financial_statements_engine.validation.pipeline import validate_draft


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
                "CashAndCashEquivalents": {"value": 30.0, "unit_scale": "crores"},
                "TotalAssets": {"value": 200.0, "unit_scale": "crores"},
                "TotalEquity": {"value": 120.0, "unit_scale": "crores"},
                "TotalLiabilities": {"value": 80.0, "unit_scale": "crores"},
                "NetCashFlowsFromUsedInOperatingActivities": {"value": 25.0, "unit_scale": "crores"},
            }
        },
        sort_keys=True,
    ).encode("utf-8")


def test_warehouse_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["never_validates_accounting"] is True
    assert h["never_stores_drafts"] is True
    assert h["consumers_must_use_contracts"] is True
    assert "dcf.v1" in h["contracts"]


def test_vfqe_publishes_into_warehouse(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:fwh1",
    )
    result = validate_draft(draft)
    assert result["approval"]["publishable"] is True
    wh = (result.get("publish_result") or {}).get("warehouse") or {}
    assert wh.get("published") is True
    assert wh.get("fact_n", 0) >= 1
    latest = get_latest("TCS")
    assert latest["n"] >= 1
    assert all(f.get("immutable") for f in latest["facts"])
    events = {e["event_type"] for e in get_bus().tail(100)}
    assert "warehouse.facts_published.v1" in events


def test_rejected_never_enters_warehouse(fse_tmp):
    pack = {
        "approval_status": "REJECTED",
        "validation_id": "val:rej",
        "facts": [{"metric": "revenue", "value": 1.0, "statement_type": "income_statement"}],
        "ticker": "TCS",
    }
    out = publish_validated_pack(validated_pack=pack)
    assert out["published"] is False
    assert get_latest("TCS")["n"] == 0


def test_facts_immutable_no_overwrite(fse_tmp):
    draft = parse_bytes(
        "INFY",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:fwh2",
    )
    a = validate_draft(draft)
    facts = ((a.get("publish_result") or {}).get("warehouse") or {}).get("facts") or []
    assert facts
    f0 = facts[0]
    path = fact_path(f0["company_id"], f0["fact_id"], f0["version"])
    assert path.exists()
    with pytest.raises(FileExistsError):
        from financial_statements_engine.financial_warehouse.storage.roots import store_fact_record

        store_fact_record(f0)


def test_versioning_creates_new_version(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:fwh3a",
    )
    validate_draft(draft)
    # Second validation/publish creates v2 for same fact keys
    draft2 = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:fwh3b",
    )
    validate_draft(draft2)
    # history should have multiple entries
    hist = list((warehouse_root() / "history").glob("*.jsonl"))
    assert hist
    lines = hist[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2


def test_data_contracts(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:fwh4",
    )
    validate_draft(draft)
    assert contracts()["ok"] is True
    dcf = contract("dcf.v1", "TCS")
    assert dcf["ok"] is True
    assert dcf["direct_storage_access"] is False
    assert dcf["data"]["facts"]
    scr = contract("screener.v1", "TCS")
    assert "revenue" in scr["data"]["metrics"]
    ask = contract("ask_agib.v1", "TCS")
    assert ask["data"]["snapshot"]


def test_time_travel_views(fse_tmp):
    draft = parse_bytes(
        "TCS",
        _rich_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:fwh5",
    )
    validate_draft(draft)
    latest = time_travel("TCS", "latest")
    assert latest["ok"] is True
    original = time_travel("TCS", "original")
    assert original["ok"] is True
    assert original["n"] >= 1


def test_dashboard(fse_tmp):
    dash = dashboard()
    assert dash["warehouse_health"] == "ok"
    assert "storage_dashboard" in dash
