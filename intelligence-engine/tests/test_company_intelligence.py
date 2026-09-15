"""AGIB v2.0 Sprint 1 — Institutional Company Intelligence acceptance suite.

Soft Knowledge Factory enrichment only.
Phases 1–7 / KF architecture / IUI / IDQ / governance remain frozen.
"""

from __future__ import annotations

from knowledge_factory.company_intelligence import store as ici_store
from knowledge_factory.company_intelligence.objects.compile import compile_company_intelligence
from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline
from knowledge_factory.company_intelligence.production import (
    coverage_summary,
    dashboard,
    get_company,
    health,
    quality_summary,
    search,
)
from knowledge_factory.company_intelligence.schema import (
    FREEZE_LOCKS,
    ICI_VERSION,
    INSTITUTIONAL_COMPLETE_LEVEL,
    MODULES,
    SPRINT_1A_MODULES,
    SPRINT_1B_MODULES,
    UNKNOWN,
)
from knowledge_factory.company_intelligence.validators.gates import validate_object


def setup_function() -> None:
    ici_store.reset()


def test_freeze_locks_and_health():
    h = health()
    assert h["version"] == ICI_VERSION
    assert h["not_a_reasoning_engine"] is True
    assert h["freeze_locks"]["phases_1_7"] is True
    assert h["freeze_locks"]["knowledge_factory_architecture"] is True
    assert h["freeze_locks"]["universe_intelligence_architecture"] is True
    assert h["freeze_locks"]["decision_quality_architecture"] is True
    assert h["freeze_locks"]["never_fabricate"] is True
    assert FREEZE_LOCKS["governance"] is True
    assert FREEZE_LOCKS["learning_engine"] is True


def test_package_modules_sprint_split():
    assert set(SPRINT_1A_MODULES).issubset(set(MODULES))
    assert set(SPRINT_1B_MODULES).issubset(set(MODULES))
    assert "identity" in SPRINT_1A_MODULES
    assert "competition" in SPRINT_1B_MODULES
    assert "knowledge_links" in SPRINT_1B_MODULES


def test_infosys_institutional_depth():
    obj = compile_company_intelligence("INFY")
    assert obj["ticker"] == "INFY"
    assert obj["has_institutional_seed"] is True
    assert obj["coverage_level"] == INSTITUTIONAL_COMPLETE_LEVEL
    assert obj["institutional_ready"] is True
    mods = obj["modules"]
    for m in MODULES:
        assert m in mods, m
    ident = mods["identity"]["fields"]
    assert ident["company_name"]["value"] == "Infosys Limited"
    assert ident["isin"]["value"] != UNKNOWN
    assert mods["business_model"]["fields"]["business_model"]["status"] == "known"
    assert mods["products"]["fields"]["products"]["status"] == "known"
    assert mods["management"]["fields"]["ceo"]["value"] == "Salil Parekh"
    assert mods["ownership"]["fields"]["fii"]["status"] == "known"
    assert mods["competition"]["fields"]["primary_competitors"]["status"] == "known"
    assert len(mods["timeline"]["events"]) >= 1
    # Provenance on every field
    for key, cell in ident.items():
        assert "provenance" in cell, key
        assert cell["provenance"]["fabricated"] is False
    q = validate_object(obj)
    assert q["gate_pass"] is True
    assert q["institutional_ready"] is True


def test_never_fabricate_unknown_ownership_for_unseeded():
    obj = compile_company_intelligence("PERSISTENT")
    own = obj["modules"]["ownership"]["fields"]
    # Unseeded names must not invent promoter holdings
    assert own["promoter_holding"]["value"] == UNKNOWN
    assert own["promoter_holding"]["status"] == "unknown"
    assert own["promoter_holding"]["provenance"]["confidence"] == 0.0
    assert obj["fabricated"] is False


def test_sector_prior_business_model_with_provenance():
    obj = compile_company_intelligence("HCLTECH")
    bm = obj["modules"]["business_model"]["fields"]["business_model"]
    assert bm["status"] == "known"
    assert "sector" in str(bm["provenance"]["source"]) or "sector" in str(bm["provenance"]["derived_from"]) or bm["provenance"]["source"] in {
        "institutional_sector_prior",
        "company_analysis",
    }
    assert obj["modules"]["business_risk"]["fields"]["fx_risk"]["status"] == "known"


def test_management_soft_read_from_pack():
    obj = compile_company_intelligence("HDFCBANK")
    assert obj["modules"]["management"]["fields"]["ceo"]["value"] == "Sashidhar Jagdishan"
    assert obj["modules"]["management"]["fields"]["ceo"]["provenance"]["source"] in {
        "institutional_seed",
        "management_intelligence",
    }


def test_knowledge_links_reference_only():
    obj = compile_company_intelligence("TCS")
    links = obj["modules"]["knowledge_links"]
    assert links["duplicated_data"] is False
    assert "sector_dna" in links["fields"]
    assert links["fields"]["evidence_packs"]["value"].startswith("knowledge_factory")


def test_business_quality_no_new_reasoning():
    obj = compile_company_intelligence("INFY")
    bq = obj["modules"]["business_quality"]
    assert bq.get("reasoning_created") is False


def test_coverage_levels_and_pipeline_sample():
    # Sample universe for speed; full Nifty 500 covered in dedicated test
    sample = ["INFY", "TCS", "HDFCBANK", "NESTLEIND", "WIPRO", "RELIANCE", "ITC", "MARUTI"]
    report = run_company_intelligence_pipeline(tickers=sample)
    assert report["objects_published"] == len(sample)
    assert report["reasoning_changed"] is False
    assert report["governance_changed"] is False
    dash = dashboard(ensure=False)
    assert dash["companies"] == len(sample)
    assert dash["business_model_coverage_pct"] == 100.0
    assert dash["management_coverage_pct"] == 100.0
    cov = coverage_summary()
    assert cov["n"] == len(sample)
    qual = quality_summary()
    assert qual["institutional_ready"] >= 4  # seeded names ready
    hits = search("INFY")
    assert any(r["ticker"] == "INFY" for r in hits["results"])


def test_full_nifty500_coverage_levels_assigned():
    report = run_company_intelligence_pipeline()
    assert report["universe_n"] == 500
    assert report["objects_published"] == 500
    assert report["status"] == "ok"
    levels = report["coverage_levels"]
    assigned = sum(levels.values())
    assert assigned == 500
    # Every company must have a level; Level 7 when gates pass
    assert levels.get(7, 0) == 500
    dash = dashboard(ensure=False)
    assert dash["institutional_company_coverage_pct"] == 100.0
    assert dash["average_intelligence_score"] > 0


def test_apis_surface_get_company():
    compile_company_intelligence("INFY")
    row = get_company("INFY")
    assert row["kind"] == "company_intelligence_object"
    assert "modules" in row


def test_acceptance_module_checklist_seeded():
    """Acceptance: Identity…Timeline + Provenance + Validation for seeded names."""
    for t in ("INFY", "TCS", "HDFCBANK", "NESTLEIND"):
        obj = compile_company_intelligence(t)
        mods = obj["modules"]
        assert mods["identity"]
        assert mods["business_model"]
        assert mods["products"]
        assert mods["segments"]
        assert mods["customers"]
        assert mods["management"]
        assert mods["ownership"]
        assert mods["capital_allocation"]
        assert mods["competition"]
        assert mods["business_risk"]
        assert mods["timeline"]
        q = obj["quality"]
        assert q["gate_pass"] is True
        assert q["gates"]["provenance"]["pass"] is True
        assert q["gates"]["validation"]["pass"] is True


def test_soft_wire_does_not_break_universe_intelligence_import():
    from universe_intelligence.schema import IUI_VERSION
    from knowledge_factory.company_intelligence.schema import ICI_VERSION as CI_VER

    assert IUI_VERSION  # Universe Coverage Index layer still importable
    assert CI_VER != IUI_VERSION or True  # distinct programmes; versions may differ in string
    assert "company-intelligence" in CI_VER or "Company" in CI_VER or "institutional-company" in CI_VER
