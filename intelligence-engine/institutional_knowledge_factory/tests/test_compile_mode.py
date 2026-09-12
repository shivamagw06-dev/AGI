"""Compile mode and KPE tests."""

from __future__ import annotations

from institutional_knowledge_factory import (
    calculate_maturity,
    compile_company,
    gather_sources,
    health,
    load_iko,
)
from institutional_knowledge_factory.persist import store_root


def test_health_shows_two_modes():
    h = health()
    assert h["engine"] == "Knowledge Production Engine (KPE)"
    assert "compile" in h["execution_modes"]
    assert "incremental" in h["execution_modes"]
    assert h["architecture_freeze"] == "v1.0"


def test_gather_sources_tcs():
    sources = gather_sources("TCS")
    assert sources["entity_id"] == "TCS"
    assert "ikt" in sources["sources_used"] or sources["ikt"] is not None


def test_compile_company_persists():
    store_root()
    result = compile_company("TCS", company="Tata Consultancy Services", force=True)
    assert result["mode"] == "compile"
    assert result["enabled"] is True
    assert result.get("iko")
    assert result["iko"].get("compiled_at")
    assert result.get("maturity", {}).get("institutional_grade")

    persisted = load_iko("TCS")
    assert persisted is not None
    assert persisted.get("compiled_at")


def test_compile_improves_claims_beyond_unknown():
    result = compile_company("INFY", force=True)
    claims = result["iko"]["claims"]
    non_unknown = [c for c in claims if c["state"] != "UNKNOWN"]
    assert len(non_unknown) >= 1


def test_maturity_has_dna_dimensions():
    result = compile_company("HDFCBANK", force=True)
    maturity = calculate_maturity(result["iko"])
    assert "knowledge_maturity" in maturity
    assert "institutional_grade" in maturity
    assert maturity.get("identity") or "identity" in maturity.get("knowledge_maturity", {})
