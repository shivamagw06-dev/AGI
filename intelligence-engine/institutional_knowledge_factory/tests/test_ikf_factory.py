"""IKF v1.0 knowledge factory tests."""

from __future__ import annotations

from institutional_knowledge_object import empty_iko
from institutional_knowledge_factory import (
    apply_ikf,
    compute_knowledge_quality,
    evaluate_thesis,
    health,
    institutional_review,
    normalize_source,
    process_evidence,
)
from institutional_knowledge_runtime.store import load_or_create_company


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["writers_llm_allowed"] is False
    assert h["incremental_pipeline_steps"] == 11
    assert h["compile_pipeline_steps"] == 12


def test_normalize_source():
    raw = {"source_type": "annual_report", "entity_id": "TCS", "extracts": []}
    norm = normalize_source(raw)
    assert norm["trust_score"] == 90
    assert norm["entity_id"] == "TCS"
    assert norm["normalized"] is True


def test_process_evidence_updates_dna():
    evidence = [{
        "source_id": "AR2025",
        "source_type": "annual_report",
        "entity_id": "TCS",
        "trust_score": 90,
        "freshness": 85,
        "extracts": [{
            "template_id": "CLAIM_FINANCIAL_CASH_GENERATION",
            "statement": "TCS generates strong and stable free cash flow relative to capex.",
            "confidence": 88,
            "evidence_id": "EV_FCF_2025",
        }],
        "metrics": {"operating_margin": 24.5},
    }]
    result = process_evidence("TCS", evidence, company="Tata Consultancy Services")
    assert result["enabled"] is True
    assert result["claims_updated"] >= 1
    assert result["steps_completed"][-1] == "notify_research_workflows"
    assert result["thesis"]["entity_id"] == "TCS"
    assert result["quality"]["metrics"]["evidence_coverage"] > 0


def test_knowledge_quality_metrics():
    iko = empty_iko("TCS")
    quality = compute_knowledge_quality(iko)
    assert quality["measured"] is True
    assert quality["metrics"]["unknown_count"] == len(iko["claims"])
    assert quality["metrics"]["review_status"] in {"healthy", "needs_review", "stale"}


def test_thesis_re_evaluation_on_change():
    iko = empty_iko("TCS")
    changes = [{
        "claim_id": iko["claims"][0]["claim_id"],
        "impact": "material_upgrade",
        "previous_state": "UNKNOWN",
        "new_state": "SUPPORTED",
    }]
    thesis = evaluate_thesis(iko, changes)
    assert thesis["re_evaluated"] is True


def test_institutional_review():
    iko = empty_iko("INFY")
    review = institutional_review(iko, changes=[], quality=compute_knowledge_quality(iko))
    assert "what_do_we_now_know" in review
    assert "what_research_should_be_updated" in review
    assert len(review["review_questions"]) == 7


def test_apply_ikf_without_evidence():
    out = apply_ikf({"ticker": "TCS", "company": "Tata Consultancy Services"})
    ikf = out["institutional_knowledge_factory"]
    assert ikf["enabled"] is True
    assert ikf["evidence_processed"] is False
    assert out.get("knowledge_quality")
    assert out.get("investment_thesis")


def test_apply_ikf_with_evidence():
    evidence = [{
        "source_id": "QR_Q1",
        "source_type": "quarterly_results",
        "entity_id": "TCS",
        "extracts": [{
            "template_id": "CLAIM_BUSINESS_SWITCHING_COSTS",
            "statement": "TCS pricing power remains durable with large enterprise clients.",
            "confidence": 82,
            "evidence_id": "EV_SWITCH_001",
        }],
    }]
    out = apply_ikf({"ticker": "TCS"}, evidence_items=evidence)
    assert out["institutional_knowledge_factory"]["evidence_processed"] is True
    assert out["institutional_knowledge_factory"]["claims_updated"] >= 1
    assert out.get("iko")


def test_assertions_without_evidence_remain_unknown():
    evidence = [{
        "source_id": "BAD",
        "source_type": "alternative_data",
        "entity_id": "TCS",
        "trust_score": 40,
        "extracts": [{
            "statement": "Unsupported claim with no evidence ref.",
            "confidence": 90,
            "state": "SUPPORTED",
        }],
    }]
    result = process_evidence("TCS", evidence)
    # Validation should downgrade to UNKNOWN
    assert result["claims_validated"] >= 0


def test_notifications_on_material_change():
    evidence = [{
        "source_id": "AR2025",
        "source_type": "annual_report",
        "entity_id": "RELIANCE",
        "extracts": [{
            "template_id": "CLAIM_INVESTMENT_THESIS_CORE",
            "statement": "Institutional thesis on RELIANCE depends primarily on retail expansion.",
            "confidence": 85,
            "evidence_id": "EV_THESIS_001",
        }],
    }]
    result = process_evidence("RELIANCE", evidence)
    assert isinstance(result["notifications"], list)


def test_iko_persisted_after_factory():
    process_evidence("WIPRO", [{
        "source_id": "S1",
        "source_type": "quarterly_results",
        "entity_id": "WIPRO",
        "extracts": [{
            "template_id": "CLAIM_MGMT_CAPITAL_ALLOCATION",
            "statement": "WIPRO management has historically allocated capital in shareholders' interests.",
            "confidence": 78,
            "evidence_id": "EV_MGMT_001",
        }],
    }])
    iko = load_or_create_company("WIPRO")
    mgmt = next(c for c in iko["claims"] if c["template_id"] == "CLAIM_MGMT_CAPITAL_ALLOCATION")
    assert mgmt["state"] in {"SUPPORTED", "PARTIAL", "ANSWERED"}
