"""Company Identity Service — canonical classification contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _store(monkeypatch):
    monkeypatch.setenv(
        "VALUATION_CONSENSUS_ROOT", str(ROOT / "data" / "valuation_consensus")
    )
    from company_identity.service import invalidate_cache

    invalidate_cache()
    yield
    invalidate_cache()


def _has_master() -> bool:
    from valuation_consensus.store import load_live

    return bool((load_live().get("rows") or {}))


GOLDEN_EXPECTATIONS = {
    "AXISBANK": ("Financials", "Diversified Banks", "Universal Bank", "banks"),
    "HDFCBANK": ("Financials", "Diversified Banks", "Universal Bank", "banks"),
    "SBIN": ("Financials", "Diversified Banks", "Universal Bank", "banks"),
    "ONGC": ("Energy", "Integrated Oil and Gas", "Integrated Energy Company", "oil_gas"),
    "INFY": ("Information Technology", "IT Consulting and Other Services", "IT Services", "it_services"),
    "APOLLOHOSP": ("Health Care", "Health Care Facilities", "Hospital Network", "hospitals"),
    "INDIGO": ("Industrials", "Passenger Airlines", "Airline", "airlines"),
    "JSWSTEEL": ("Materials", "Steel", "Steel Producer", "metals"),
    "DLF": ("Real Estate", "Diversified Real Estate Activities", "Real Estate Operator", "real_estate"),
    "POWERGRID": ("Utilities", "Electric Utilities", "Electric Utility", "utilities"),
    "BHARTIARTL": (
        "Communication Services",
        "Wireless Telecommunication Services",
        "Telecom Operator",
        "telecom",
    ),
}


def test_golden_companies_resolve_canonically():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.service import identity_for

    for ticker, (sector, industry, business_type, dna) in GOLDEN_EXPECTATIONS.items():
        ident = identity_for(ticker)
        assert ident.resolved, ticker
        assert ident.primary_sector == sector, ticker
        assert ident.primary_industry == industry, ticker
        assert ident.business_type == business_type, ticker
        assert ident.industry_dna == dna, ticker


def test_axis_bank_is_never_a_conglomerate_or_oil_company():
    """The production bug: Axis Bank returned conglomerate + GRM drivers."""
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.service import identity_for

    ident = identity_for("AXISBANK")
    assert ident.business_type == "Universal Bank"
    assert "conglomerate" not in (ident.business_type or "").lower()
    assert ident.industry_dna == "banks"
    for banned in ("GRM", "Production", "Reserve Replacement", "Crack Spread"):
        assert banned not in ident.allowed_valuation
    for kpi in ("CASA", "NIM", "GNPA", "CET1"):
        assert kpi in ident.kpis


def test_every_company_classifies():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.service import health

    report = health()
    assert report["ok"] is True
    assert report["classification_pct"] == 100.0
    assert report["unmapped_industries"] == []


def test_only_canonical_primary_sectors_are_emitted():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.schema import PRIMARY_SECTORS
    from company_identity.service import identity_for
    from valuation_consensus.store import list_tickers

    for ticker in list_tickers()[:400]:
        sector = identity_for(ticker).primary_sector
        assert sector is None or sector in PRIMARY_SECTORS, ticker


def test_mention_resolution_never_binds_a_namesake():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.service import resolve_company_mention

    assert resolve_company_mention("Apollo Hospitals")[0] == "APOLLOHOSP"
    assert resolve_company_mention("Apollo Tyres")[0] == "APOLLOTYRE"
    assert resolve_company_mention("What is Indian Oil Corporation Limited's model?")[0] == "IOC"
    assert resolve_company_mention("Oil and Natural Gas Corporation Limited")[0] == "ONGC"
    # Ambiguous or uncovered mentions must refuse rather than guess.
    for text in ("Apollo", "HDFC", "Tata", "Air India", "Explain enterprise value"):
        assert resolve_company_mention(text)[0] is None, text
    # The same refusal must hold when a group stem is embedded in a question.
    for text in (
        "What sector is Tata in?",
        "What is JSW's sector?",
        "What is HDFC's industry?",
        "What sector is Apollo in?",
    ):
        assert resolve_company_mention(text)[0] is None, text
    assert resolve_company_mention("What sector is JSW Steel in?")[0] == "JSWSTEEL"
    assert resolve_company_mention("What sector is Reliance in?")[0] == "RELIANCE"


def test_metadata_router_refuses_ambiguous_group_stems():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.metadata_router import route

    for question in (
        "Tata sector", "JSW sector", "HDFC sector", "Apollo sector",
        "Sun Pharma industry", "Air India sector",
    ):
        assert route(question) is None, question
    assert route("JSW Steel sector")["ticker"] == "JSWSTEEL"
    assert route("Reliance sector")["ticker"] == "RELIANCE"


def test_guard_flags_cross_industry_leakage():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.guard import validate_text
    from company_identity.service import identity_for

    bank = identity_for("AXISBANK")
    bad = validate_text(
        bank,
        "For conglomerate, enterprise value is driven by GRM, Production, Reserve Replacement.",
    )
    assert bad.ok is False
    assert any("grm" in v.rule.lower() for v in bad.violations)

    good = validate_text(bank, "NIM, CASA and credit cost drive the bank's earnings.")
    assert good.ok is True


def test_guard_allows_shared_vocabulary_between_allied_industries():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.guard import validate_text
    from company_identity.service import identity_for

    # SSSG is retail vocabulary that FMCG legitimately shares.
    fmcg = identity_for("ITC")
    assert validate_text(fmcg, "SSSG and distribution reach drive growth.").ok is True
    # Plant load factor is a power term, not an airline leak.
    power = identity_for("NTPC")
    assert validate_text(power, "Plant load factor and availability drive returns.").ok is True


def test_guard_rejects_wrong_classification_claims():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from company_identity.guard import validate_classification
    from company_identity.service import identity_for

    bank = identity_for("AXISBANK")
    bad = validate_classification(
        bank, sector="Energy", industry="Integrated Oil and Gas", business_type="Conglomerate"
    )
    assert bad.ok is False
    rules = {v.rule for v in bad.violations}
    assert "wrong_primary_sector" in rules
    assert "wrong_primary_industry" in rules
    assert "wrong_business_type" in rules

    ok = validate_classification(
        bank,
        sector="Financials",
        industry="Diversified Banks",
        business_type="Universal Bank",
        industry_dna="banks",
    )
    assert ok.ok is True


def test_ask_answer_is_classification_consistent():
    if not _has_master():
        pytest.skip("CapIQ master not seeded")
    from knowledge_unification.production import plan_and_gather

    out = plan_and_gather("Axis Bank")
    text = " ".join([out.get("summary") or ""] + [str(w) for w in (out.get("why") or [])]).lower()
    for banned in ("grm", "reserve replacement", "refining complexity"):
        assert banned not in text
    assert "business type: conglomerate" not in text

    identity = (out.get("diagnostics") or {}).get("company_identity") or {}
    assert identity.get("primary_sector") == "Financials"
    assert identity.get("business_type") == "Universal Bank"
