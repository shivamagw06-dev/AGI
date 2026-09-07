"""FSE-04 — Parsing & Normalization Engine + Schema Evolution tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.parsing.production import health, parse_bytes
from financial_statements_engine.schema_evolution.production import health as se_health
from financial_statements_engine.schema_evolution.service import resolve_label
from financial_statements_engine.store import store_root
from financial_statements_engine.warehouse import publish_statement


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _sample_json_pack() -> bytes:
    pack = {
        "fields": {
            "Revenue From Operations": {"value": 100.0, "unit_scale": "crores"},
            "PAT": {"value": 20.0, "unit_scale": "crores"},
            "MysteryLineItemXYZ": {"value": 1.0, "unit_scale": "crores"},
            "EmptyMetric": {"value": None, "unit_scale": "crores"},
        }
    }
    return json.dumps(pack, sort_keys=True).encode("utf-8")


def test_parsing_health(fse_tmp):
    h = health()
    assert h["status"] == "ok"
    assert h["workstream_id"] == "FSE-04"
    assert h["writes_warehouse"] is False
    assert h["validates_accounting"] is False
    assert h["issues_recommendations"] is False


def test_schema_evolution_health_and_resolve(fse_tmp):
    h = se_health()
    assert h["status"] == "ok"
    assert h["version"].startswith("schema-evolution-")
    r = resolve_label("RevenueFromOperations", as_of="2024-03-31", reporting_standard="IND_AS")
    assert r["ok"] is True
    assert r["canonical"] == "revenue"
    assert r["via"] == "schema_evolution"


def test_determinism_same_bytes_same_fingerprint(fse_tmp):
    data = _sample_json_pack()
    a = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:det1",
    )
    b = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:det1",
    )
    assert a["ok"] and b["ok"]
    assert a["deterministic_fingerprint"] == b["deterministic_fingerprint"]


def test_maps_via_registry_not_parser_local(fse_tmp):
    result = parse_bytes(
        "TCS",
        _sample_json_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:map1",
    )
    metrics = result["mapped"]["metrics"]
    assert "revenue" in metrics
    assert "net_income" in metrics
    assert result["mapped"]["uses_parser_local_synonyms"] is False
    assert "MysteryLineItemXYZ" in result["mapped"]["unknown_fields"]


def test_missing_value_stays_null(fse_tmp):
    result = parse_bytes(
        "TCS",
        _sample_json_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:null1",
    )
    # EmptyMetric is unknown (not in registry) — still preserved as unknown with null
    unknown = result["mapped"]["unknown_fields"]["EmptyMetric"]
    assert unknown["value"] is None


def test_pdf_quarantined_not_warehouse(fse_tmp):
    result = parse_bytes(
        "TCS",
        b"%PDF-1.4 fake",
        document_type="pdf",
        evidence_id="sha256:pdf1",
    )
    assert result.get("quarantined") is True
    assert result.get("writes_warehouse") is False
    published = store_root() / "published"
    assert not published.exists() or not any(published.rglob("*.json"))


def test_traceability_evidence_on_facts(fse_tmp):
    result = parse_bytes(
        "RELIANCE",
        _sample_json_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:trace1",
    )
    assert result["ok"]
    assert result["drafts"]
    for draft in result["drafts"]:
        for fact in draft["facts"]:
            assert fact["evidence"]["evidence_id"] == "sha256:trace1"
            assert fact["status"] == "draft"


def test_pipeline_does_not_publish_warehouse(fse_tmp, monkeypatch):
    called = {"n": 0}

    def _boom(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("warehouse publish must not be called from PNE")

    monkeypatch.setattr(
        "financial_statements_engine.warehouse.publish_statement",
        _boom,
    )
    # also ensure import path unused
    result = parse_bytes(
        "INFY",
        _sample_json_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:nowh1",
    )
    assert result["ok"]
    assert result["writes_warehouse"] is False
    assert called["n"] == 0


def test_parse_completed_event(fse_tmp):
    parse_bytes(
        "NTPC",
        _sample_json_pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:evt1",
    )
    types = {e["event_type"] for e in get_bus().tail(50)}
    assert "parse.started" in types
    assert "parse.completed" in types
