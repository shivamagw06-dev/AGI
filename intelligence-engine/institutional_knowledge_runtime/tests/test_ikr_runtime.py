"""IKR v1.0 runtime tests."""

from __future__ import annotations

import pytest

from institutional_knowledge_object import empty_iko
from institutional_knowledge_runtime import (
    apply_ikr_runtime,
    calculate_confidence,
    health,
    list_unknowns,
    load_object,
    resolve_dependencies,
    run_pipeline,
    select_assertions,
    update_assertion,
    validate_assertions,
    version_assertion,
)
from institutional_knowledge_runtime.assertions import claim_to_assertion


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["writers_llm_allowed"] is False


def test_pipeline_loads_assertions_from_iko():
    iko = empty_iko("TCS", company="Tata Consultancy Services")
    pack = run_pipeline(iko)
    assert pack["enabled"] is True
    assert len(pack["assertions"]) == len(iko["claims"])
    assert pack["steps_completed"][-1] == "return_validated"
    assert pack["validation"]["total"] == len(iko["claims"])


def test_unknowns_exposed():
    iko = empty_iko("TCS")
    unknowns = list_unknowns(iko)
    assert len(unknowns) == len(iko["claims"])
    assert unknowns[0]["priority"] in ("high", "medium")


def test_dependency_propagation():
    parent = {
        "assertion_id": "CLAIM_TCS_MARGINS",
        "status": "CONTRADICTED",
        "dependencies": [],
        "confidence": 50,
        "evidence_refs": [{"evidence_id": "EV1"}],
    }
    child = {
        "assertion_id": "CLAIM_TCS_PRICING",
        "status": "SUPPORTED",
        "dependencies": ["CLAIM_TCS_MARGINS"],
        "confidence": 90,
        "evidence_refs": [{"evidence_id": "EV2"}],
    }
    resolved = resolve_dependencies([parent, child])
    by_id = {a["assertion_id"]: a for a in resolved}
    assert by_id["CLAIM_TCS_PRICING"]["status"] == "UNDER_REVIEW"


def test_confidence_deterministic():
    assertion = claim_to_assertion({
        "claim_id": "C1",
        "state": "SUPPORTED",
        "confidence": 80,
        "evidence_refs": [{"evidence_id": "EV1"}],
    })
    evidence = {
        "supporting": [{"evidence_id": "EV1", "source_quality": 90, "freshness": 85}],
    }
    conf = calculate_confidence(assertion, evidence)
    assert "formula" in conf
    assert "inputs" in conf
    assert "weights" in conf
    assert 0 <= conf["result"] <= 100


def test_contradiction_detection():
    iko = empty_iko("TCS")
    iko["claims"][0]["state"] = "SUPPORTED"
    iko["claims"][0]["evidence_refs"] = [{"evidence_id": "EV1"}]
    iko["claims"][0]["contradictions"] = ["CLAIM_OTHER"]
    pack = run_pipeline(iko, evidence_graph={
        "items": [{"evidence_id": "EV1", "role": "supporting", "source_quality": 80, "freshness": 80}],
    })
    contradicted = [a for a in pack["assertions"] if a["assertion_id"] == iko["claims"][0]["claim_id"]]
    assert contradicted[0]["status"] == "CONTRADICTED"


def test_version_assertion_append_only():
    assertion = claim_to_assertion({"claim_id": "C1", "state": "PARTIAL", "version": 1, "history": []})
    updated = version_assertion(assertion, reason="Evidence added", source="evidence_pipeline", evidence_added=["EV2"])
    assert updated["version"] == 2
    assert len(updated["history"]) == 1
    assert updated["history"][0]["previous_version"] == 1


def test_update_assertion_rejects_llm():
    iko = empty_iko("TCS")
    cid = iko["claims"][0]["claim_id"]
    with pytest.raises(PermissionError):
        update_assertion(iko, cid, {"status": "SUPPORTED"}, writer="llm", reason="test")


def test_update_assertion_approved_writer():
    iko = empty_iko("TCS")
    cid = iko["claims"][0]["claim_id"]
    updated = update_assertion(
        iko,
        cid,
        {"status": "PARTIAL", "confidence": 60, "evidence_refs": [{"evidence_id": "EV1"}]},
        writer="evidence_pipeline",
        reason="Initial evidence",
    )
    claim = next(c for c in updated["claims"] if c["claim_id"] == cid)
    assert claim["state"] == "PARTIAL"
    assert claim["version"] == 2


def test_select_assertions():
    iko = empty_iko("TCS")
    pack = run_pipeline(iko)
    sel = select_assertions(pack, include_unknowns=True, limit=5)
    assert sel["count"] <= 5
    assert "unknowns" in sel


def test_apply_ikr_runtime_wiring():
    out = apply_ikr_runtime({"ticker": "TCS", "company": "Tata Consultancy Services"})
    ikr = out["institutional_knowledge_runtime"]
    assert ikr["enabled"] is True
    assert ikr["entity_id"] == "TCS"
    assert "selection" in ikr
    assert out.get("institutional_unknowns")


def test_validate_supported_requires_evidence():
    assertion = claim_to_assertion({
        "claim_id": "C1",
        "state": "SUPPORTED",
        "confidence": 90,
        "evidence_refs": [],
    })
    v = validate_assertions([assertion])
    assert v["passed"] is False


def test_load_object_company():
    pack = load_object("company", "INFY", company="Infosys")
    assert pack["enabled"] is True
    assert pack["entity_id"] == "INFY"
