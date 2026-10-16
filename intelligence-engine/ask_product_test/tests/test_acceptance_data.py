"""Tests for CI acceptance data bootstrap and health checks."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ask_product_test.acceptance_data import (
    GOLDEN_TICKERS,
    bootstrap_acceptance_data,
    check_acceptance_data,
    fixtures_root,
)


@pytest.fixture
def isolated_data(tmp_path, monkeypatch):
    """Simulate CI — empty data dir, tracked fixtures only."""
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("KIP_DATA_DIR", str(data))
    monkeypatch.setenv("VALUATION_CONSENSUS_ROOT", str(data / "valuation_consensus"))
    monkeypatch.setenv("IKT_STORE_ROOT", str(data / "institutional_knowledge_tables"))
    monkeypatch.setenv("KF_STORE_ROOT", str(data / "knowledge_factory"))
    monkeypatch.setenv("IERE_STORE_ROOT", str(data / "evidence_retrieval"))
    monkeypatch.setenv("ACCEPTANCE_FIXTURES_ROOT", str(fixtures_root()))
    yield data


def test_fixtures_manifest_exists():
    manifest = fixtures_root() / "manifest.json"
    assert manifest.exists(), "acceptance_fixtures must be committed"
    payload = json.loads(manifest.read_text())
    assert payload["counts"]["valuation_consensus_rows"] >= 10


def test_health_fails_without_bootstrap(isolated_data):
    report = check_acceptance_data(verbose=False)
    assert report["status"] == "FAIL"
    assert report["failure_class"] == "INFRASTRUCTURE"


def test_bootstrap_populates_data(isolated_data):
    result = bootstrap_acceptance_data(verbose=False)
    assert result["bootstrapped"] is True
    assert result["files_copied"] > 0
    health = result["health"]
    assert health["status"] == "PASS"


def test_golden_tickers_present_after_bootstrap(isolated_data):
    bootstrap_acceptance_data(verbose=False)
    vc_path = isolated_data / "valuation_consensus" / "live.json"
    rows = json.loads(vc_path.read_text())["rows"]
    for ticker in GOLDEN_TICKERS:
        assert ticker in rows, f"Missing golden ticker {ticker}"


def test_canonical_classification_not_zero_after_bootstrap(isolated_data):
    bootstrap_acceptance_data(verbose=False)
    from ask_product_test.canonical_classification_acceptance_v1 import run

    report = run(target_questions=50)
    assert report["decision"] != "NOT_EVALUATED"
    assert report["total"] > 0
