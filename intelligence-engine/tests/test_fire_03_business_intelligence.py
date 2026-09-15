"""FIRE-03 — Business & Management Intelligence deterministic tests."""

from __future__ import annotations

from business_intelligence.evidence import make_fact
from business_intelligence.extractors.engine_extract import (
    extract_capital,
    extract_governance,
    extract_guidance,
    extract_profile,
    extract_risks,
    extract_segments,
    extract_strategy,
)
from business_intelligence.fixtures import sample_ample_bundles, sample_infy_style_bundles
from business_intelligence.production import (
    company,
    guidance,
    health,
    risks,
    segments,
    strategy,
)
from business_intelligence.report import build_report
from business_intelligence.schema import (
    CAT_RISK,
    REPORT_SECTIONS,
    VERSION,
    WORKSTREAM_ID,
)


def test_fire03_health():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["version"] == VERSION
    assert h["uses_llm"] is False
    assert h["buy_sell"] is False
    assert h["is_summariser"] is False
    assert h["is_evidence_extraction_engine"] is True
    assert h["fire_01_unchanged"] is True
    assert h["fire_02_unchanged"] is True
    assert h["never_mutates_warehouse"] is True


def test_business_profile_extraction():
    bundles = sample_ample_bundles()
    facts = extract_profile(bundles)
    cats = {f["category"] for f in facts}
    assert "Business Description" in cats or "Operating Model" in cats
    assert "Products" in cats or "Services" in cats
    assert "Geographic Exposure" in cats
    assert all(f.get("page") is not None for f in facts)
    assert all(f.get("section") for f in facts)
    assert all(f.get("document") for f in facts)
    assert all(f.get("evidence") for f in facts)


def test_segment_extraction():
    facts = extract_segments(sample_ample_bundles())
    assert facts
    assert any("Specialty Chemicals" in (f.get("statement") or "") or "segment" in (f.get("statement") or "").lower() for f in facts)
    assert any(f.get("category") in {"Business Segments", "Segment Analysis"} for f in facts)
    assert all(f.get("page") is not None for f in facts)


def test_risk_extraction_disclosed_only():
    facts = extract_risks(sample_ample_bundles())
    labels = " ".join(f.get("statement") or "" for f in facts).lower()
    assert "commodity" in labels
    assert "currency" in labels
    assert "cyber" in labels
    assert all(f.get("category") == CAT_RISK for f in facts)
    # No inferred risk themes outside text
    assert "pandemic" not in labels


def test_management_strategy_extraction():
    facts = extract_strategy(sample_ample_bundles())
    blob = " ".join(f.get("statement") or "" for f in facts).lower()
    assert "export" in blob or "growth" in blob
    assert "digital" in blob or "ai" in blob or "capacity" in blob
    assert all(f.get("section") for f in facts)


def test_capital_allocation_extraction():
    facts = extract_capital(sample_ample_bundles())
    blob = " ".join(f.get("statement") or "" for f in facts).lower()
    assert "dividend" in blob or "buyback" in blob or "capital" in blob
    # FKB soft link present on capital facts
    assert any(f.get("fkb_refs") for f in facts)


def test_guidance_extraction_explicit_only():
    facts = extract_guidance(sample_ample_bundles())
    assert facts
    assert any("guidance" in (f.get("statement") or "").lower() or "outlook" in (f.get("statement") or "").lower() for f in facts)


def test_governance_extraction():
    facts = extract_governance(sample_ample_bundles())
    blob = " ".join(f.get("statement") or "" for f in facts).lower()
    assert "board" in blob or "related" in blob or "governance" in blob


def test_evidence_and_page_references():
    report = build_report("AMPLE", documents=sample_ample_bundles())
    facts = report["facts"]
    assert facts
    assert all(f.get("evidence") for f in facts)
    assert all(f.get("page") is not None for f in facts)
    assert all(f.get("section") for f in facts)
    assert all(f.get("document") for f in facts)
    assert all(f.get("reporting_period") for f in facts)
    assert all(f.get("confidence") in {"High", "Medium", "Low"} for f in facts)
    src = report["sections"]["source_references"]
    assert src["n_sources"] >= 1
    assert src["facts_with_page"] == len(facts)


def test_bir_sections_present():
    report = build_report("AMPLE", documents=sample_ample_bundles())
    for sec in REPORT_SECTIONS:
        assert sec in report["sections"]
    assert report["report_code"] == "BIR"
    assert report["BusinessProfile"] is not None
    assert report["RiskRegister"]
    assert report["ManagementStrategy"]


def test_api_facades():
    docs = sample_infy_style_bundles()
    pack = company("INFY", documents=docs)
    assert pack["ok"] is True
    assert pack["n_facts"] >= 1
    assert pack["fire_01_unchanged"] is True
    assert segments("INFY", documents=docs)["n"] >= 1
    assert strategy("INFY", documents=docs)["n"] >= 1
    assert risks("INFY", documents=docs)["n"] >= 1
    assert guidance("INFY", documents=docs)["n"] >= 1
    mc = pack["mission_control"]
    assert mc["business_documents_processed"] == 2
    assert mc["facts_extracted"] >= 1
    assert "confidence_distribution" in mc


def test_fkb_glossary_soft_link():
    fact = make_fact(
        category="Cash Deployment",
        statement="Capital allocation commentary disclosed",
        evidence="Capital allocation described.",
        page=10,
        section="CAPITAL_ALLOCATION",
        document="Annual Report FY2026",
        document_type="ANNUAL_REPORT",
        reporting_period="FY2026",
        fkb_hints=["capital allocation"],
    )
    assert fact["fkb_refs"]
    assert any(r.get("glossary_id") == "CapitalAllocation" for r in fact["fkb_refs"])


def test_regression_fire01_fire02_unchanged():
    """FIRE-03 must not alter FIRE-01 / FIRE-02 public façades."""
    from financial_intelligence.production import company as fire01_company
    from financial_intelligence.production import financial_drivers, health as fire01_health
    from financial_intelligence.drivers.production import health as fire02_health

    h1 = fire01_health()
    assert h1["workstream_id"] == "FIRE-01"
    assert "buy_sell" in h1 and h1["buy_sell"] is False

    h2 = fire02_health()
    assert h2["workstream_id"] == "FIRE-02"
    assert h2["fire_01_unchanged"] is True

    # Shape smoke — empty warehouse still returns ok structure
    r1 = fire01_company("ZZZNOCOMPANY")
    assert "workstream_id" in r1
    r2 = financial_drivers("ZZZNOCOMPANY")
    assert "workstream_id" in r2

    # FIRE-03 pack keys are additive and separate
    r3 = company("AMPLE", documents=sample_ample_bundles())
    assert r3["workstream_id"] == "FIRE-03"
    assert "findings" not in r3 or r3.get("facts") is not None
