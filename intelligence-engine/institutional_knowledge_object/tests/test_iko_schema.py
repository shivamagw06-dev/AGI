"""IKO v2.0 claim-centric schema tests."""

from __future__ import annotations

from institutional_knowledge_object import (
    CLAIM_REGISTRY,
    assemble_claim_bullets,
    claims_for_investment_assessment,
    compute_completeness,
    empty_iko,
    validate_claim,
)


def test_empty_iko_has_registry_claims():
    iko = empty_iko("TCS", company="Tata Consultancy Services")
    assert iko["iko_version"] == "iko-v2.0.0"
    assert len(iko["claims"]) == len(CLAIM_REGISTRY)
    assert all(c["state"] == "UNKNOWN" for c in iko["claims"])
    assert iko["completeness"]["unknown"] == len(CLAIM_REGISTRY)
    assert iko["completeness"]["no_percentages"] is True
    assert "progress_pct" not in iko["completeness"]


def test_validate_supported_requires_evidence():
    claim = {
        "claim_id": "C1",
        "statement": "TCS has switching costs.",
        "claim_type": "business",
        "state": "SUPPORTED",
        "confidence": 90,
        "evidence_refs": [],
    }
    v = validate_claim(claim)
    assert v["valid"] is False
    assert "supported_requires_evidence" in v["issues"]


def test_validate_rejects_buy_language():
    claim = {
        "claim_id": "C2",
        "statement": "You must buy this stock now.",
        "claim_type": "investment",
        "state": "ANSWERED",
        "confidence": 50,
    }
    v = validate_claim(claim)
    assert v["valid"] is False


def test_investment_assessment_claim_selection():
    iko = empty_iko("TCS")
    iko["claims"][0]["state"] = "SUPPORTED"
    iko["claims"][0]["claim_type"] = "business"
    iko["claims"][0]["confidence"] = 88
    iko["claims"][0]["evidence_refs"] = [{"evidence_id": "EV1"}]
    selected = claims_for_investment_assessment(iko)
    assert selected[0]["state"] == "SUPPORTED"


def test_assemble_claim_bullets():
    bullets = assemble_claim_bullets(
        [{"statement": "Cash generation remains strong.", "state": "SUPPORTED", "confidence": 91}]
    )
    assert "Cash generation" in bullets[0]
    assert "SUPPORTED" in bullets[0]


def test_completeness_counts():
    claims = [
        {"state": "SUPPORTED"},
        {"state": "UNKNOWN"},
        {"state": "CONTRADICTED"},
    ]
    c = compute_completeness(claims)
    assert c["supported"] == 1
    assert c["unknown"] == 1
    assert c["contradicted"] == 1
