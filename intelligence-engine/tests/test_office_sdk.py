"""Office SDK — shared application contract tests."""

from __future__ import annotations

from office_sdk.contracts import (
    SCHEMA_EVIDENCE_BLOCK,
    SCHEMA_REQUEST,
    SCHEMA_RESPONSE,
    confidence_summary,
    evidence_block,
    evidence_reference,
    normalize_block,
    office_metadata,
    office_request,
    office_response,
    provenance_bundle,
)
from office_sdk.domains import list_domains
from office_sdk.production import domains, health, invoke, office_catalog
from office_sdk.registry import catalog, dispatch, get_office
from office_sdk.schema import (
    DOMAIN_PORTFOLIO,
    DOMAIN_RESEARCH,
    SDK_VERSION,
    SDK_WORKSTREAM_ID,
)


def _io_prebuilt():
    from tests.test_io_01_investment_office import _prebuilt

    return _prebuilt()


def _cio_universe():
    from tests.test_cio_01_comparative_intelligence import _universe

    return _universe()


def test_health():
    h = health()
    assert h["workstream_id"] == SDK_WORKSTREAM_ID
    assert h["version"] == SDK_VERSION
    assert "io-01" in h["live_offices"]
    assert "cio-01" in h["live_offices"]
    assert "po-01" in h["live_offices"]
    assert "wo-01" in h["live_offices"]
    assert "so-01" in h["planned_offices"]
    assert h["buy_sell"] is False


def test_domains_include_research_and_portfolio():
    d = list_domains()
    ids = {x["domain"] for x in d}
    assert DOMAIN_RESEARCH in ids
    assert DOMAIN_PORTFOLIO in ids
    research = next(x for x in d if x["domain"] == DOMAIN_RESEARCH)
    assert research["live_count"] == 2
    portfolio = next(x for x in d if x["domain"] == DOMAIN_PORTFOLIO)
    assert any(o["office_id"] == "po-01" and o["status"] == "live" for o in portfolio["offices"])


def test_catalog_contract():
    cat = catalog()
    assert cat["contract"]["request"] == SCHEMA_REQUEST
    assert cat["contract"]["response"] == SCHEMA_RESPONSE
    assert "io-01" in cat["dispatchable"]
    assert "cio-01" in cat["dispatchable"]
    assert "po-01" in cat["dispatchable"]
    assert "wo-01" in cat["dispatchable"]


def test_evidence_block_shape():
    b = evidence_block(
        "Revenue improving",
        module="FIRE-01",
        evidence_ids=["ev:1"],
        confidence=0.8,
        reporting_period="FY2026",
        tickers=["TCS"],
    )
    assert b["schema"] == SCHEMA_EVIDENCE_BLOCK
    assert b["module"] == "FIRE-01"
    assert b["evidence_ids"] == ["ev:1"]
    assert b["tickers"] == ["TCS"]


def test_normalize_block_from_legacy():
    legacy = {
        "text": "hello",
        "module": "FIRE-06",
        "evidence_ids": ["a"],
        "confidence": 0.5,
        "reporting_period": "FY2026",
    }
    b = normalize_block(legacy)
    assert b["schema"] == SCHEMA_EVIDENCE_BLOCK
    assert b["text"] == "hello"


def test_office_response_guardrails():
    meta = office_metadata(
        office_id="io-01",
        workstream_id="IO-01",
        product="Investment Office",
        version="io-01",
        domain=DOMAIN_RESEARCH,
        buy_sell=False,
        recalculates=False,
    )
    resp = office_response(
        metadata=meta,
        report_type="institutional_research_package",
        confidence=confidence_summary(mean_confidence=0.7, ok_count=2, total=2),
        provenance=provenance_bundle(
            references=[evidence_reference("e1", module="FIRE-01", confidence=0.7)],
            modules_invoked=["FIRE-01"],
        ),
    )
    assert resp["schema"] == SCHEMA_RESPONSE
    assert resp["guardrails"]["buy_sell"] is False
    assert resp["ok"] is True


def test_dispatch_io():
    req = office_request(
        office_id="io-01",
        tickers=["TCS"],
        question="How strong is the balance sheet?",
        options={"prebuilt": _io_prebuilt()},
    )
    resp = dispatch(req)
    assert resp["ok"] is True
    assert resp["metadata"]["office_id"] == "io-01"
    assert resp["report_type"] == "institutional_research_package"
    assert resp["sections"]
    assert resp["provenance"]["references"]
    # Shared block schema on sections
    assert resp["sections"][0]["blocks"][0]["schema"] == SCHEMA_EVIDENCE_BLOCK


def test_dispatch_cio():
    req = office_request(
        office_id="cio-01",
        tickers=["HDFCBANK", "ICICIBANK"],
        question="Compare HDFCBANK and ICICIBANK",
        options={"prebuilt_map": _cio_universe()},
    )
    resp = dispatch(req)
    assert resp["ok"] is True
    assert resp["metadata"]["office_id"] == "cio-01"
    assert resp["metadata"]["compares_only"] is True
    assert resp["report_type"] == "institutional_comparison_report"
    assert resp["payload"]["tickers"] == ["HDFCBANK", "ICICIBANK"]


def test_invoke_unknown_office():
    out = invoke({"office_id": "so-01", "tickers": ["TCS"]})
    assert out["ok"] is False
    assert "not dispatchable" in str(out.get("error") or "")


def test_get_office():
    o = get_office("IO-01")
    assert o is not None
    assert o["office_id"] == "io-01"
    assert o["domain"] == DOMAIN_RESEARCH


def test_production_domains_catalog():
    d = domains()
    assert d["ok"] is True
    c = office_catalog()
    assert c["ok"] is True
    assert len(c["offices"]) >= 5


def test_io_make_block_uses_sdk_schema():
    from investment_office.irp.assemble import make_block

    b = make_block(
        text="x",
        module="FIRE-01",
        evidence_ids=["e"],
        confidence=0.9,
        reporting_period="FY2026",
    )
    assert b["schema"] == SCHEMA_EVIDENCE_BLOCK
    assert b["confidence"] == 0.9


def test_cio_block_uses_sdk_schema():
    from comparative_intelligence.report import _block

    b = _block(
        "y",
        module="FIRE-06",
        evidence_ids_list=["e"],
        confidence=0.7,
        tickers=["A", "B"],
    )
    assert b["schema"] == SCHEMA_EVIDENCE_BLOCK
    assert b["tickers"] == ["A", "B"]


def test_regression_io_cio_still_pass_shapes():
    from investment_office.production import company
    from comparative_intelligence.production import compare_companies

    io = company("TCS", question="Explain TCS.", prebuilt=_io_prebuilt())
    assert io["ok"] is True
    assert io["irp"]["sections"]
    # blocks now carry schema but retain required provenance fields
    block = io["irp"]["sections"][0]["blocks"][0]
    assert "module" in block and "evidence_ids" in block and "confidence" in block

    cio = compare_companies(
        ["HDFCBANK", "ICICIBANK"],
        prebuilt_map=_cio_universe(),
    )
    assert cio["ok"] is True
    assert cio["icr"]["sections"]
