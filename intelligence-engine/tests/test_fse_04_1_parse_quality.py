"""FSE-04.1 — Parse Manifest, Replay & Certification tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.parsing.production import parse_bytes
from financial_statements_engine.parsing.quality.certification import certify_parser
from financial_statements_engine.parsing.quality.gates import evaluate_gates
from financial_statements_engine.parsing.quality.manifest import list_manifests, load_manifest
from financial_statements_engine.parsing.quality.production import health
from financial_statements_engine.parsing.quality.unknown_queue import list_queue
from financial_statements_engine.raw_evidence import store_raw
from financial_statements_engine.store import store_root


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _pack_with_unknown() -> bytes:
    return json.dumps(
        {
            "fields": {
                "Revenue From Operations": {"value": 100.0, "unit_scale": "crores"},
                "PAT": {"value": 20.0, "unit_scale": "crores"},
                "WeirdUnknownLabelZZZ": {"value": 3.0, "unit_scale": "crores"},
            }
        },
        sort_keys=True,
    ).encode("utf-8")


def test_quality_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == "FSE-04.1"
    assert "parse_manifest" in h["capabilities"]
    assert h["issues_recommendations"] is False


def test_parse_always_has_immutable_manifest(fse_tmp):
    r = parse_bytes(
        "TCS",
        _pack_with_unknown(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:m1",
    )
    assert r["ok"]
    assert r["manifest_id"]
    assert r["draft_id"]
    assert r["manifest"]["immutable"] is True
    assert Path(r["manifest_path"]).exists()
    # cannot overwrite same manifest id
    from financial_statements_engine.parsing.quality.manifest import store_manifest

    with pytest.raises(FileExistsError):
        store_manifest(r["manifest"])


def test_reparse_creates_new_draft_keeps_old(fse_tmp):
    data = _pack_with_unknown()
    a = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:m2a",
    )
    b = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:m2b",
    )
    assert a["manifest_id"] != b["manifest_id"]
    assert a["draft_id"] != b["draft_id"]
    assert Path(a["draft_path"]).exists()
    assert Path(b["draft_path"]).exists()
    assert load_manifest("TCS", a["manifest_id"]) is not None
    assert len(list_manifests("TCS")) >= 2


def test_multi_stage_confidence(fse_tmp):
    r = parse_bytes(
        "TCS",
        _pack_with_unknown(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:conf1",
    )
    c = r["confidence"]
    for key in ("extraction", "normalization", "structural", "overall"):
        assert key in c


def test_hierarchy_preserved(fse_tmp):
    data = json.dumps(
        {
            "fields": {
                "Revenue > Revenue From Operations > Domestic Revenue": {
                    "value": 60.0,
                    "unit_scale": "crores",
                },
                "PAT": {"value": 10.0, "unit_scale": "crores"},
            }
        },
        sort_keys=True,
    ).encode("utf-8")
    r = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:hier1",
    )
    assert r["hierarchy"]["flattening_destroys_hierarchy"] is False
    assert r["hierarchy"]["statement_tree"]
    assert r["hierarchy_fingerprint"]


def test_unknown_enters_review_queue(fse_tmp):
    parse_bytes(
        "TCS",
        _pack_with_unknown(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:unk1",
    )
    open_q = list_queue(status="open")
    labels = {r["label"] for r in open_q}
    assert "WeirdUnknownLabelZZZ" in labels


def test_replay_does_not_mutate_raw(fse_tmp):
    data = _pack_with_unknown()
    meta = store_raw(
        ticker="TCS",
        data=data,
        source="nse_xbrl",
        document_type="json",
        period_type="annual",
        period_end="2025-03-31",
    )
    first = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id=meta["evidence_id"],
    )
    from financial_statements_engine.parsing.quality.replay import replay
    from financial_statements_engine.raw_evidence import read_raw_bytes

    before = read_raw_bytes("TCS", meta["evidence_id"])
    report = replay(
        ticker="TCS",
        evidence_id=meta["evidence_id"],
        prior_manifest_id=first["manifest_id"],
        meta={"period_end": "2025-03-31", "period_type": "annual", "document_type": "json"},
    )
    after = read_raw_bytes("TCS", meta["evidence_id"])
    assert before == after
    assert report["raw_evidence_modified"] is False
    assert report["historical_drafts_overwritten"] is False
    assert report.get("diff") is not None
    assert Path(first["draft_path"]).exists()


def test_versioned_events_emitted(fse_tmp):
    parse_bytes(
        "TCS",
        _pack_with_unknown(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:evt41",
    )
    types = {e["event_type"] for e in get_bus().tail(100)}
    assert "parse.completed.v1" in types
    assert "draft.created.v1" in types
    assert "unknown_metric.queued.v1" in types


def test_certification_and_gates(fse_tmp):
    report = certify_parser()
    assert "production_eligible" in report
    assert "gates" in report
    # fixture should map all expected metrics → eligible
    assert report["ok"] is True
    assert report["production_eligible"] is True

    failed = evaluate_gates(
        {
            "metric_extraction_accuracy_pct": 90.0,
            "canonical_mapping_accuracy_pct": 99.9,
            "unknown_metric_rate_pct": 0.1,
            "hierarchy_preservation_pct": 100.0,
            "replay_determinism_pct": 100.0,
            "duplicate_draft_rate_pct": 0.0,
            "traceability_pct": 100.0,
            "benchmark_pass_rate_pct": 100.0,
        }
    )
    assert failed["production_eligible"] is False
    assert "metric_extraction_accuracy_pct" in failed["failed_gates"]


def test_no_warehouse_from_quality_parse(fse_tmp):
    parse_bytes(
        "INFY",
        _pack_with_unknown(),
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="sha256:nowh41",
    )
    published = store_root() / "published"
    assert not published.exists() or not any(published.rglob("*.json"))
