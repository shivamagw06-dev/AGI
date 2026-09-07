"""IO-01 — Institutional Investment Office deterministic tests."""

from __future__ import annotations

from investment_office.irp.assemble import (
    _dedupe_blocks,
    blocks_for_module,
    confidence_summary,
    make_block,
    merge_evidence_catalog,
)
from investment_office.irp.coordinator import InvestmentCoordinator, coordinate
from investment_office.irp.packages import modules_for_package, normalize_package_type
from investment_office.irp.routing import route_question
from investment_office.production import company, health, query, soft_slice_mission_control
from investment_office.schema import (
    IO01_VERSION,
    IO01_WORKSTREAM_ID,
    IRP_SECTIONS,
    MODULE_FIRE01,
    MODULE_FIRE02,
    MODULE_FIRE03,
    MODULE_FIRE04,
    MODULE_FIRE05,
    MODULE_FIRE06,
    PACKAGE_BALANCE_SHEET,
    PACKAGE_BUSINESS_QUALITY,
    PACKAGE_EVIDENCE_REVIEW,
    PACKAGE_EXECUTION_REVIEW,
    PACKAGE_INSTITUTIONAL_BRIEF,
)
from investment_office import store as io_store


def _prebuilt() -> dict[str, dict]:
    return {
        MODULE_FIRE01: {
            "ticker": "TCS",
            "period": "FY2026",
            "confidence": 0.81,
            "summary": "Revenue improving over the reporting window.",
            "trends": [
                {
                    "id": "t1",
                    "metric": "revenue",
                    "direction": "improving",
                    "evidence_ids": ["ev:rev:1"],
                    "confidence": 0.8,
                },
                {
                    "id": "t2",
                    "metric": "operating_margin",
                    "direction": "stable",
                    "evidence_ids": ["ev:om:1"],
                    "confidence": 0.75,
                },
            ],
            "evidence_ids": ["ev:rev:1", "ev:om:1"],
        },
        MODULE_FIRE02: {
            "ticker": "TCS",
            "period": "FY2026",
            "confidence": 0.77,
            "relationships": [
                {
                    "id": "r1",
                    "name": "revenue→cash",
                    "status": "supported",
                    "evidence_ids": ["ev:rel:1"],
                    "confidence": 0.7,
                },
                {
                    "id": "r2",
                    "name": "leverage",
                    "status": "strong balance sheet signal",
                    "evidence_ids": ["ev:lev:1"],
                    "confidence": 0.72,
                },
            ],
            "evidence_ids": ["ev:rel:1", "ev:lev:1"],
        },
        MODULE_FIRE03: {
            "ticker": "TCS",
            "period": "FY2026",
            "confidence": 0.7,
            "facts": [
                {
                    "id": "bf1",
                    "text": "IT services business with enterprise clients",
                    "evidence_ids": ["ev:bf:1"],
                    "confidence": 0.7,
                }
            ],
            "evidence_ids": ["ev:bf:1"],
        },
        MODULE_FIRE04: {
            "ticker": "TCS",
            "period": "FY2026",
            "confidence": 0.66,
            "assessments": [
                {
                    "id": "a1",
                    "claim": "Strategy expansion",
                    "status": "Supported",
                    "evidence_ids": ["ev:ef:1"],
                    "confidence": 0.65,
                },
                {
                    "id": "a2",
                    "claim": "Margin guidance",
                    "status": "Partial",
                    "evidence_ids": ["ev:ef:2"],
                    "confidence": 0.6,
                },
            ],
            "evidence_ids": ["ev:ef:1", "ev:ef:2"],
        },
        MODULE_FIRE05: {
            "ticker": "TCS",
            "period": "FY2026",
            "confidence": 0.68,
            "objectives": [
                {
                    "objective_id": "obj1",
                    "title": "Margin expansion",
                    "status": "Delivered",
                    "evidence_ids": ["ev:me:1"],
                    "confidence": 0.7,
                },
                {
                    "objective_id": "obj2",
                    "title": "New geography",
                    "status": "Not Yet",
                    "evidence_ids": ["ev:me:2"],
                    "confidence": 0.55,
                },
            ],
            "evidence_ids": ["ev:me:1", "ev:me:2"],
            "outstanding_questions": ["Confirm timing of geography ramp."],
        },
        MODULE_FIRE06: {
            "ticker": "TCS",
            "period": "FY2026",
            "confidence": 0.74,
            "overall_score": 0.71,
            "overall_label": "solid",
            "pillars": [
                {
                    "pillar": "growth",
                    "score": 0.8,
                    "label": "strong",
                    "evidence_ids": ["ev:bq:g"],
                    "confidence": 0.8,
                },
                {
                    "pillar": "balance_sheet",
                    "score": 0.78,
                    "label": "strong",
                    "evidence_ids": ["ev:bq:bs"],
                    "confidence": 0.76,
                },
            ],
            "evidence_ids": ["ev:bq:g", "ev:bq:bs"],
        },
    }


def test_health_includes_io01():
    h = health()
    assert h["not_an_engine"] is True
    assert h["io01"]["workstream_id"] == IO01_WORKSTREAM_ID
    assert h["io01"]["version"] == IO01_VERSION
    assert h["io01"]["orchestrates_only"] is True
    assert h["io01"]["buy_sell"] is False
    assert h["io01"]["never_recalculates"] is True


def test_question_routing_balance_sheet():
    r = route_question("How strong is the balance sheet?")
    assert r["package_type"] == PACKAGE_BALANCE_SHEET
    assert r["modules"] == [MODULE_FIRE02, MODULE_FIRE06]


def test_question_routing_what_changed():
    r = route_question("What changed this year?")
    assert set(r["modules"]) == {MODULE_FIRE01, MODULE_FIRE02}


def test_question_routing_management_delivered():
    r = route_question("Has management delivered?")
    assert r["package_type"] == PACKAGE_EXECUTION_REVIEW
    assert r["modules"] == [MODULE_FIRE05]


def test_question_routing_strategy_supported():
    r = route_question("Is management's strategy supported?")
    assert r["package_type"] == PACKAGE_EVIDENCE_REVIEW
    assert set(r["modules"]) == {MODULE_FIRE03, MODULE_FIRE04}


def test_question_routing_explain_company():
    r = route_question("Explain TCS.")
    assert r["package_type"] == PACKAGE_INSTITUTIONAL_BRIEF
    assert MODULE_FIRE01 in r["modules"]
    assert MODULE_FIRE06 in r["modules"]


def test_question_routing_business_quality():
    r = route_question("How strong is the business?")
    assert r["package_type"] == PACKAGE_BUSINESS_QUALITY


def test_explicit_package_override():
    r = route_question("anything", package_type=PACKAGE_BALANCE_SHEET)
    assert r["intent"] == "explicit_package"
    assert r["modules"] == list(modules_for_package(PACKAGE_BALANCE_SHEET))


def test_normalize_package_type():
    assert normalize_package_type("balance sheet review") == PACKAGE_BALANCE_SHEET
    assert normalize_package_type(PACKAGE_INSTITUTIONAL_BRIEF) == PACKAGE_INSTITUTIONAL_BRIEF


def test_module_orchestration_only_required():
    io_store.reset_for_tests()
    irp = coordinate(
        ticker="TCS",
        question="How strong is the balance sheet?",
        prebuilt=_prebuilt(),
    )
    assert set(irp["modules_invoked"]) == {MODULE_FIRE02, MODULE_FIRE06}
    assert irp["guardrails"]["recalculates"] is False
    assert irp["guardrails"]["buy_sell"] is False
    # Pass-through scores unchanged
    assert irp["module_payloads"][MODULE_FIRE06]["payload"]["overall_score"] == 0.71


def test_duplicate_removal():
    blocks = [
        make_block(text="Revenue improving", module="FIRE-01", evidence_ids=["a"], confidence=0.8),
        make_block(text="Revenue improving", module="FIRE-01", evidence_ids=["a"], confidence=0.8),
        make_block(text="Revenue improving", module="FIRE-01", evidence_ids=["b"], confidence=0.8),
    ]
    out = _dedupe_blocks(blocks)
    assert len(out) == 2


def test_evidence_confidence_reference_preservation():
    pre = _prebuilt()
    collected = {
        m: {"ok": True, "module": m, "payload": p}
        for m, p in pre.items()
    }
    refs = merge_evidence_catalog(collected)
    ids = {r["evidence_id"] for r in refs}
    assert "ev:rev:1" in ids
    assert "ev:bq:bs" in ids
    # confidence preserved from module payload
    conf = confidence_summary(collected)
    by = {r["module"]: r["confidence"] for r in conf["by_module"]}
    assert by[MODULE_FIRE01] == 0.81
    assert by[MODULE_FIRE06] == 0.74

    blocks = blocks_for_module(MODULE_FIRE05, collected[MODULE_FIRE05])
    assert any("Delivered" in (b.get("text") or "") for b in blocks)
    assert all("module" in b and "evidence_ids" in b and "confidence" in b for b in blocks)


def test_irp_sections_and_provenance():
    irp = InvestmentCoordinator().coordinate(
        ticker="TCS",
        question="Explain the business.",
        prebuilt=_prebuilt(),
    )
    keys = [s["key"] for s in irp["sections"]]
    assert "executive_summary" in keys
    assert "evidence_references" in keys
    assert "confidence_summary" in keys
    # every narrative block has provenance fields
    for sec in irp["sections"]:
        for b in sec["blocks"]:
            assert "module" in b
            assert "evidence_ids" in b
            assert "confidence" in b
            assert "reporting_period" in b


def test_production_company_and_query():
    io_store.reset_for_tests()
    pack = company("TCS", question="Explain TCS.", prebuilt=_prebuilt())
    assert pack["ok"] is True
    assert pack["workstream_id"] == IO01_WORKSTREAM_ID
    assert pack["orchestrates_only"] is True
    assert pack["irp"]["package_type"] == PACKAGE_INSTITUTIONAL_BRIEF

    q = query(ticker="TCS", question="Has management delivered?", prebuilt=_prebuilt())
    assert q["modules_invoked"] == [MODULE_FIRE05]

    metrics = io_store.irp_metrics()
    assert metrics["requests_served"] == 2
    assert metrics["modules_invoked_total"] >= 1
    assert "average_assembly_time_ms" in metrics


def test_soft_slice_mission_control():
    io_store.reset_for_tests()
    company("TCS", package_type=PACKAGE_BALANCE_SHEET, prebuilt=_prebuilt())
    slice_ = soft_slice_mission_control()
    assert slice_["workstream_id"] == IO01_WORKSTREAM_ID
    assert slice_["panels"]["requests_served"] >= 1
    assert "modules_invoked" in slice_["panels"]
    assert "average_assembly_time" in slice_["panels"]
    assert "evidence_reuse" in slice_["panels"]
    assert "coverage" in slice_["panels"]
    assert "confidence" in slice_["panels"]


def test_no_score_mutation():
    pre = _prebuilt()
    original = pre[MODULE_FIRE06]["overall_score"]
    irp = coordinate(ticker="TCS", package_type=PACKAGE_BUSINESS_QUALITY, prebuilt=pre)
    assert irp["module_payloads"][MODULE_FIRE06]["payload"]["overall_score"] == original
    assert pre[MODULE_FIRE06]["overall_score"] == original


def test_institutional_brief_covers_irp_section_catalog():
    # Full brief should include all IRP section keys
    irp = coordinate(ticker="TCS", package_type=PACKAGE_INSTITUTIONAL_BRIEF, prebuilt=_prebuilt())
    keys = {s["key"] for s in irp["sections"]}
    assert set(IRP_SECTIONS).issubset(keys)


def test_regression_existing_desk_health():
    """Desk health contract from Investment Office v1 remains intact."""
    h = health()
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["version"]
    assert h["not_a_recommendation_engine"] is True
