"""Unit tests for Phase 3.1 Industry Intelligence Engine (pre-Ask wiring)."""

from __future__ import annotations

from industry_intelligence.dna_catalog import INDUSTRY_DNA, get_dna, list_industries
from industry_intelligence.orchestrator import analyse, detect_intents
from industry_intelligence.production import health, industry, soft_slice_for_ask_agi
from industry_intelligence.registry import resolve_industry
from industry_intelligence.schema import ASK_WIRED, II_VERSION


REQUIRED = {
    "banks",
    "nbfc",
    "insurance",
    "asset_management",
    "it_services",
    "software",
    "retail",
    "fmcg",
    "consumer_durables",
    "automobile",
    "auto_components",
    "telecom",
    "hospitals",
    "diagnostics",
    "pharma",
    "chemicals",
    "cement",
    "power",
    "renewables",
    "utilities",
    "oil_gas",
    "metals",
    "mining",
    "capital_goods",
    "infrastructure",
    "real_estate",
    "airlines",
    "logistics",
    "shipping",
    "hotels",
    "media",
    "education",
    "agriculture",
    "qsr",
    "internet_platforms",
    "data_centers",
}


def test_registry_coverage():
    keys = set(list_industries())
    assert keys == REQUIRED
    assert len(INDUSTRY_DNA) == 36


def test_every_industry_has_dna_fields():
    for key in REQUIRED:
        d = get_dna(key)
        assert d is not None
        assert d.revenue_drivers and d.kpis and d.valuation_methods
        assert d.regulators and d.typical_risks
        assert d.primary_cycle and d.competitive_structure
        assert d.fabricated is False


def test_alias_resolve():
    assert resolve_industry("SaaS") == "software"
    assert resolve_industry("insurers") == "insurance"
    assert resolve_industry("oil & gas") == "oil_gas"
    assert resolve_industry("quick service restaurants") == "qsr"


def test_ask_wired_via_kul():
    assert ASK_WIRED is True
    h = health()
    assert h["ask_wired"] is True
    assert h.get("ask_wired_via")
    assert h["uses_llm"] is False
    soft = soft_slice_for_ask_agi("Why do banks use P/B?")
    assert soft["found"] is True
    assert soft["ask_wired"] is True


def test_analyse_banks_pb():
    out = analyse("Why do banks use P/B?", industry="banks")
    assert out["ok"] is True
    assert out["fabricated"] is False
    assert "p/b" in out["summary"].lower() or "book" in out["summary"].lower()
    assert out.get("valuation") or out.get("cross_industry")


def test_kpi_casa():
    out = analyse("What is CASA and why does it matter for banks?", industry="banks")
    assert out.get("kpis")
    blob = (out["summary"] + str(out["kpis"])).lower()
    assert "casa" in blob


def test_competition_intent():
    assert "competition" in detect_intents("Describe competitive structure in Banks.")
    out = analyse("Describe competitive structure in Banks.", industry="banks")
    assert out.get("competition", {}).get("found") is True


def test_industry_package():
    pkg = industry("hospitals")
    assert pkg["found"] is True
    assert pkg["dna"]["found"] is True
    assert pkg["economics"]["found"] is True
    assert pkg["valuation"]["found"] is True


def test_version():
    assert II_VERSION.startswith("3.1")
