"""FSE-04.2 — Evidence Coverage Matrix & Extraction Audit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.parsing.coverage.diff import diff_coverage
from financial_statements_engine.parsing.coverage.matrix import build_coverage_matrix
from financial_statements_engine.parsing.coverage.production import analytics, dashboard, health
from financial_statements_engine.parsing.coverage.schema import EVIDENCE_DOMAINS, EXTRACTION_STATUSES
from financial_statements_engine.parsing.coverage.scorecard import build_scorecard
from financial_statements_engine.parsing.coverage.store import store_matrix
from financial_statements_engine.parsing.production import parse_bytes


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _pack() -> bytes:
    return json.dumps(
        {
            "fields": {
                "Revenue From Operations": {"value": 100.0, "unit_scale": "crores"},
                "PAT": {"value": 20.0, "unit_scale": "crores"},
                "PBT": {"value": 28.0, "unit_scale": "crores"},
                "WeirdUnknownLabelZZZ": {"value": 3.0, "unit_scale": "crores"},
            }
        },
        sort_keys=True,
    ).encode("utf-8")


def test_coverage_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == "FSE-04.2"
    assert "evidence_coverage_matrix" in h["capabilities"]
    assert h["observational_only"] is True
    assert h["blocks_publication"] is False
    assert h["validates_accounting"] is False
    assert h["issues_recommendations"] is False


def test_every_parse_emits_immutable_coverage_matrix(fse_tmp):
    r = parse_bytes(
        "TCS",
        _pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:cov1",
    )
    assert r["ok"]
    assert r["coverage_matrix_id"]
    assert r["coverage_matrix"]["immutable"] is True
    assert r["coverage_matrix"]["observational_only"] is True
    assert r["coverage_matrix"]["manifest_id"] == r["manifest_id"]
    assert r["coverage_matrix"]["draft_id"] == r["draft_id"]
    assert Path(r["coverage_matrix_path"]).exists()
    assert r["coverage_scorecard"]["blocks_publication"] is False
    with pytest.raises(FileExistsError):
        store_matrix(r["coverage_matrix"])


def test_every_domain_has_exact_status(fse_tmp):
    r = parse_bytes(
        "TCS",
        _pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:cov2",
    )
    sections = r["coverage_matrix"]["sections"]
    assert len(sections) == len(EVIDENCE_DOMAINS)
    domains = {s["domain"] for s in sections}
    assert domains == set(EVIDENCE_DOMAINS)
    for s in sections:
        assert s["status"] in EXTRACTION_STATUSES
        for key in (
            "section_name",
            "expected_metrics",
            "extracted_metrics",
            "missing_metrics",
            "unknown_labels",
            "confidence",
            "page_numbers",
            "table_count",
            "row_count",
            "parser_version",
            "processing_time_ms",
        ):
            assert key in s


def test_scorecard_and_missing_unknown_reports(fse_tmp):
    r = parse_bytes(
        "TCS",
        _pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:cov3",
    )
    sc = r["coverage_scorecard"]
    assert "coverage_percentage" in sc
    assert "unknown_label_count" in sc
    assert sc["informational_only"] is True
    assert r["missing_metric_report"]["n"] >= 1
    assert r["unknown_label_report"]["nothing_discarded"] is True
    assert any(row["original_label"] == "WeirdUnknownLabelZZZ" for row in r["unknown_label_report"]["rows"])


def test_coverage_history_and_determinism(fse_tmp):
    data = _pack()
    a = parse_bytes(
        "INFY",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:hist1",
    )
    b = parse_bytes(
        "INFY",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:hist2",
    )
    # Same document bytes → same coverage fingerprint (determinism)
    assert a["coverage_matrix"]["coverage_fingerprint"] == b["coverage_matrix"]["coverage_fingerprint"]
    assert a["coverage_matrix_id"] != b["coverage_matrix_id"]
    from financial_statements_engine.parsing.coverage.history import list_history

    hist = list_history("INFY", a["document_hash"])
    assert len(hist) >= 2


def test_coverage_diff_engine(fse_tmp):
    old = build_coverage_matrix(
        ticker="TCS",
        company_id="nse:TCS",
        evidence_id="e1",
        draft_id="draft:1",
        manifest_id="pm:1",
        document_hash="abc",
        document_type="json",
        parser_name="json_v1",
        parser_version="1.0.0",
        pne_version="1.0.0",
        metric_registry_version="1.0.0",
        processing_time_ms=10.0,
        sections_found=["income_statement"],
        metrics_extracted=["revenue"],
        unknown_fields={"WeirdX": {}},
        confidence={"overall": 0.5},
        period_info={"period_kind": "annual"},
    )
    new = build_coverage_matrix(
        ticker="TCS",
        company_id="nse:TCS",
        evidence_id="e1",
        draft_id="draft:2",
        manifest_id="pm:2",
        document_hash="abc",
        document_type="json",
        parser_name="json_v1",
        parser_version="2.0.0",
        pne_version="1.0.0",
        metric_registry_version="1.0.0",
        processing_time_ms=12.0,
        sections_found=["income_statement", "balance_sheet", "cash_flow"],
        metrics_extracted=[
            "revenue",
            "profit_before_tax",
            "net_income",
            "tax_expense",
            "finance_cost",
            "total_assets",
            "total_equity",
            "total_liabilities",
            "cash",
            "current_assets",
            "current_liabilities",
            "operating_cash_flow",
            "investing_cash_flow",
            "financing_cash_flow",
            "net_cash_change",
        ],
        unknown_fields={},
        confidence={"overall": 0.9},
        period_info={"period_kind": "annual"},
    )
    d = diff_coverage(old, new, old_scorecard=build_scorecard(old), new_scorecard=build_scorecard(new))
    assert d["coverage_gain"] > 0
    assert "WeirdX" in d["unknown_labels_resolved"]
    assert d["part_of_parser_certification"] is True


def test_mission_control_dashboard_and_analytics(fse_tmp):
    parse_bytes(
        "TCS",
        _pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:mc1",
    )
    dash = dashboard()
    assert dash["matrices_indexed"] >= 1
    assert "overall_coverage" in dash
    assert dash["blocks_publication"] is False
    an = analytics()
    assert "coverage_by_parser" in an
    assert "unknown_label_queue" in an
    events = [e["event_type"] for e in get_bus().tail(50)]
    assert "coverage.matrix.created.v1" in events
    assert "coverage.history.appended.v1" in events


def test_unsupported_and_core_statuses(fse_tmp):
    r = parse_bytes(
        "TCS",
        _pack(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:st1",
    )
    by = {s["domain"]: s["status"] for s in r["coverage_matrix"]["sections"]}
    assert by["mda"] == "UNSUPPORTED"
    assert by["notes"] == "UNSUPPORTED"
    # Partial income from revenue/PAT/PBT without full expected set
    assert by["income_statement"] in ("PARTIAL", "FOUND", "MISSING")
    assert by["cash_flow"] in ("MISSING", "NOT_PRESENT", "PARTIAL", "FOUND")
