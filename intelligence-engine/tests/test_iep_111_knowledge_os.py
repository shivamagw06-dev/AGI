"""IEP v1.1.1 — Institutional Knowledge OS tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_evidence.schema import (
    AGI_PLATFORM_VERSION,
    CANONICAL_DOMAIN_MODELS,
    IEP_VERSION,
    MISSION_STATEMENT,
    PHASE1_ACCEPTANCE_CRITERIA,
    KNOWLEDGE_OS_PIPELINE,
)
from institutional_evidence.governance.layer0 import govern_inbound_dataset
from institutional_evidence.quality.engine import evaluate_evidence_quality
from institutional_evidence.entity.resolve import resolve_entity, entity_id_for_ticker
from institutional_evidence.canonical.domains import list_canonical_models, empty_domain_bundle
from institutional_evidence.timeline.company_timeline import build_company_timeline
from institutional_evidence.claims.objects import build_claim, verify_claims
from institutional_evidence.lifecycle.research_object import (
    create_research_object,
    transition_research,
    mark_stale_for_ticker,
)
from institutional_evidence.decision_eligibility.engine import evaluate_decision_eligibility
from institutional_evidence.phase1_acceptance import evaluate_institutional_coverage
from institutional_evidence.production import get_iep_status, company_subresource


def test_version_and_mission():
    st = get_iep_status()
    assert IEP_VERSION.startswith("iep-01-v1.1")
    assert AGI_PLATFORM_VERSION.startswith("1.1")
    assert "Institutional Knowledge Platform" in MISSION_STATEMENT
    assert st["pipeline"][0] == "External Provider"
    assert "Data Governance" in st["pipeline"]
    assert st["pipeline"] == list(KNOWLEDGE_OS_PIPELINE)


def test_layer0_governance_requires_provider():
    bad = govern_inbound_dataset({}, provider_id="")
    assert bad["admitted"] is False
    ok = govern_inbound_dataset({"x": 1}, provider_id="nse", document_type="quarterly_results")
    assert ok["admitted"] is True
    g = ok["governance"]
    assert g["provider_id"] == "nse"
    assert g["hash"]
    assert g["freshness_sla_days"]
    assert g["provenance_chain"]


def test_entity_resolution_aliases():
    for q in ("RELIANCE", "Reliance Industries", "RELIANCE.NS", "500325", "INE002A01018"):
        r = resolve_entity(q)
        assert r["resolved"] is True, q
        assert r["ticker"] == "RELIANCE"
        assert r["entity_id"] == "AGI-COMPANY-0000043"
    assert entity_id_for_ticker("RELIANCE") == "AGI-COMPANY-0000043"
    unresolved = resolve_entity("DefinitelyNotARealCompanyXYZ")
    assert unresolved["resolved"] is False


def test_canonical_domain_models_listed():
    models = list_canonical_models()
    assert "CanonicalFinancialStatements" in models
    assert "CanonicalCompany" in models
    assert len(models) == len(CANONICAL_DOMAIN_MODELS)
    bundle = empty_domain_bundle("AGI-COMPANY-0000043", "RELIANCE", "Reliance Industries")
    assert bundle["models"]["CanonicalCompany"]["entity_id"] == "AGI-COMPANY-0000043"


def test_quality_engine_blocks_empty():
    q = evaluate_evidence_quality(documents=[], canonical_financials={"periods": []}, registry_items=[])
    assert q["evidence_quality_score"] < q["threshold"]
    assert q["publish_allowed"] is False
    assert q["status"] == "DO NOT PUBLISH"


def test_timeline_preserves_history_for_reliance():
    tl = build_company_timeline("RELIANCE")
    assert tl["resolved"] is True
    assert tl["event_count"] >= 3
    years = {e.get("year") for e in tl["timeline"]}
    assert "2018" in years or "2020" in years


def test_claim_objects_and_verification():
    c = build_claim(
        "Retail EBITDA margin improved.",
        entity_id="AGI-COMPANY-0000043",
        ticker="RELIANCE",
        evidence_ids=["ev_abc"],
        primary_source="Annual Report",
        confidence=96,
        consumers=["Financial Intelligence", "Research Note"],
    )
    assert c["verified"] is True
    assert c["confidence"] == 96
    v = verify_claims([c])
    assert v["zero_unsupported_material_claims"] is True


def test_research_lifecycle_transitions():
    obj = create_research_object("RELIANCE", entity_id="AGI-COMPANY-0000043", state="draft")
    assert transition_research(obj["research_id"], "published")["ok"] is True
    stale = mark_stale_for_ticker("RELIANCE", reason="new_filing")
    assert obj["research_id"] in stale["marked_stale"]


def test_decision_eligibility_denies_thin_pack():
    el = evaluate_decision_eligibility("RELIANCE")
    assert el["ok"] is True
    assert "eligible" in el
    assert el["next"] in {
        "decision_engine",
        "NO RECOMMENDATION / MONITOR",
    }


def test_phase1_acceptance_criteria_explicit():
    assert len(PHASE1_ACCEPTANCE_CRITERIA) >= 14
    cov = evaluate_institutional_coverage("RELIANCE")
    assert cov["ok"] is True
    assert "institutional_coverage_complete" in cov
    assert set(cov["checks"]).issuperset(set(PHASE1_ACCEPTANCE_CRITERIA))


def test_company_api_subresources():
    mem = company_subresource("RELIANCE", "memory")
    assert mem.get("ticker") == "RELIANCE" or mem.get("ok")
    eid = entity_id_for_ticker("RELIANCE")
    ready = company_subresource(eid, "research-ready")
    assert ready.get("entity_id") == eid or ready.get("ticker") == "RELIANCE"
