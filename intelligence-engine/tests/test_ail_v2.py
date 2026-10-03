"""AGIB Intelligence Layer V2 — living institutional intelligence tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.ail.flags import AilFlags
from app.ail.models import EvidenceRecord
from app.ail.service import AilService
from app.ail.store import AilStore
from app.main import app


def _ail() -> AilService:
    return AilService(flags=AilFlags(ail=True, ail_ask_agi=True), store=AilStore())


def test_ail_health_locked():
    h = _ail().health()
    assert h["programme"] == "AIL"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert "CDE" in h["systems"]
    assert "EL" in h["systems"]
    assert h["does_not_redesign"] == ["faa", "fre", "cae", "ask_agi"]


def test_analyse_reliance_living_intelligence():
    ail = _ail()
    pack = ail.analyse("Analyse Reliance Industries")
    assert pack["ticker"] == "RELIANCE"
    assert pack["dossier"]["version"] >= 1
    assert pack["thesis"]["bull"]["probability"] > 0
    assert pack["thesis"]["base"]["probability"] > 0
    assert pack["thesis"]["bear"]["probability"] > 0
    assert abs(
        pack["thesis"]["bull"]["probability"]
        + pack["thesis"]["base"]["probability"]
        + pack["thesis"]["bear"]["probability"]
        - 1.0
    ) < 1e-3
    assert pack["forecast"]["prediction_id"]
    assert pack["prediction_confidence"] is not None
    assert pack["ledger"]
    assert all(e.get("evidence_id") for e in pack["ledger"])
    assert pack["timeline"]["entries"]
    assert pack["knowledge_graph"]["relationships"]
    assert pack["audit_trail"]["audit_id"]
    assert pack["audit_trail"]["thesis_version"]
    assert pack["audit_trail"]["prediction_version"]


def test_dossier_incremental_not_rebuild():
    ail = _ail()
    first = ail.analyse("Analyse Reliance Industries")
    v1 = first["dossier"]["version"]
    # second analyse without new upstream evidence should not explode versions wildly
    second = ail.analyse("Analyse Reliance Industries")
    assert second["dossier"]["dossier_id"]  # living
    assert second["dossier"]["version"] >= v1
    # history retained
    assert len(ail.store.dossiers["RELIANCE"]) >= 1


def test_evidence_ledger_dedupe_and_lookup():
    ail = _ail()
    ail.analyse("Analyse Infosys")
    rows = ail.ledger("INFY")["evidence"]
    assert rows
    eid = rows[0]["evidence_id"]
    got = ail.evidence(eid)
    assert got["evidence_id"] == eid
    # re-register identical claim → same hash / same id
    again = ail.pipeline.ledger.register(
        claim=got["claim"],
        source=got["source"],
        url=got.get("url"),
        company=got.get("company"),
        ticker=got.get("ticker"),
        page=got.get("page"),
        section=got.get("section"),
        connector=got.get("connector") or "ail",
        authority_score=got.get("authority_score") or 5,
    )
    assert again.evidence_id == eid


def test_event_detection_and_timeline_link():
    ail = _ail()
    ail.pipeline.bootstrap_company("TCS")
    rec = ail.pipeline.ledger.register(
        claim="TCS raised guidance after strong large order won in banking vertical.",
        source="Exchange filing",
        url="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        company="Tata Consultancy Services",
        ticker="TCS",
        section="Announcement",
        connector="nse",
        authority_score=10,
        confidence=0.85,
    )
    events = ail.pipeline.events.detect_from_evidence(rec)
    assert events
    for e in events:
        ail.pipeline.timeline.add_from_event(e)
    listed = ail.pipeline.events.list_for("TCS")
    assert any(e["event_id"] == events[0].event_id for e in listed)
    tl = ail.timeline("TCS")
    assert any(events[0].event_id == (row.get("event_id")) for row in tl["entries"])


def test_thesis_updates_explainably_on_negative_evidence():
    ail = _ail()
    base = ail.analyse("Analyse HDFC Bank")
    before_bear = base["thesis"]["bear"]["probability"]
    rec = EvidenceRecord(
        claim="HDFC Bank cut guidance after CFO resigned amid regulatory penalty concerns.",
        source="News",
        url="https://www.business-standard.com/search?q=HDFCBANK",
        company="HDFC Bank",
        ticker="HDFCBANK",
        connector="news",
        authority_score=7,
        confidence=0.7,
    )
    stored = ail.store.put_evidence(rec)
    evts = ail.pipeline.events.detect_from_evidence(stored)
    thesis = ail.pipeline.thesis.update_with_evidence("HDFCBANK", [stored], evts)
    assert thesis.bear.probability >= before_bear
    assert any("Bear ↑" in x or "reduced base confidence" in x for x in thesis.explanation)


def test_predictions_immutable_versions():
    ail = _ail()
    a = ail.analyse("Analyse Reliance Industries")
    pid1 = a["forecast"]["prediction_id"]
    # force material thesis change then new forecast
    rec = ail.pipeline.ledger.register(
        claim="Reliance beat estimates with record revenue and margin expansion.",
        source="Quarterly results",
        url="https://www.ril.com/InvestorRelations/FinancialReporting.aspx",
        company="Reliance Industries",
        ticker="RELIANCE",
        section="Results",
        connector="company_ir",
        authority_score=10,
    )
    ail.pipeline.ingest_evidence_records("RELIANCE", [rec])
    pred = ail.pipeline.predictions.get("RELIANCE")
    assert pred["prediction_id"]
    # prior id still retrievable if versioned differently
    assert ail.prediction(pid1)["prediction_id"] == pid1
    assert pred["immutable"] is True
    assert len(pred["distributions"]) >= 8
    assert "bull" in pred["scenario"] and "bear" in pred["scenario"]


def test_monitor_watchlist_run():
    ail = _ail()
    out = ail.run_monitor(watchlist="default")
    assert out["programme"] == "CME"
    assert out["run"]["ok"] >= 1


def test_package_for_ask_agi():
    ail = _ail()
    pkg = ail.package_for_ask_agi("Analyse Reliance Industries")
    assert pkg["enabled"] is True
    assert pkg["ticker"] == "RELIANCE"
    assert pkg["dossier"]
    assert pkg["thesis"]
    assert pkg["forecast"]["prediction_id"]
    assert pkg["audit_trail"]


@pytest.mark.asyncio
async def test_ail_http_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer dev-intelligence-token"}
        health = await client.get("/v1/ail/health", headers=headers)
        assert health.status_code == 200
        assert health.json()["programme"] == "AIL"

        analyse = await client.get(
            "/v1/ail/analyse",
            params={"q": "Analyse Reliance Industries"},
            headers=headers,
        )
        assert analyse.status_code == 200
        body = analyse.json()
        assert body["ticker"] == "RELIANCE"
        assert body["dossier"]
        assert body["thesis"]
        assert body["forecast"]

        dossier = await client.get("/v1/company/RELIANCE/dossier", headers=headers)
        assert dossier.status_code == 200
        thesis = await client.get("/v1/company/RELIANCE/thesis", headers=headers)
        assert thesis.status_code == 200
        forecast = await client.get("/v1/company/RELIANCE/forecast", headers=headers)
        assert forecast.status_code == 200
        ledger = await client.get("/v1/company/RELIANCE/ledger", headers=headers)
        assert ledger.status_code == 200
        assert ledger.json()["count"] >= 1

        eid = ledger.json()["evidence"][0]["evidence_id"]
        ev = await client.get(f"/v1/evidence/{eid}", headers=headers)
        assert ev.status_code == 200
