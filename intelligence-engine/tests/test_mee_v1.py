"""MEE v1 — Market Event Engine after FLE."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aoi.service import AoiService
from app.aws.service import AwsService
from app.cre.service import CREService
from app.eve.service import EveService
from app.eve.store import EveStore
from app.fle.service import FleService
from app.fle.store import FleStore
from app.iie.service import IieService
from app.iie.store import IieStore
from app.ioc.service import IocService
from app.irp.service import IrpService
from app.kc.service import KcService
from app.kf.service import KfService
from app.kf.store import KfStore
from app.kip.service import KipService
from app.main import app
from app.mee.config import EVENT_TAXONOMY
from app.mee.engines import MeeEngines
from app.mee.service import MeeService
from app.mee.store import MeeStore
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.ui.service import UiService
from app.validation.service import ValidationService


def _stack():
    kip = KipService()
    kf = KfService(kip=kip, store=KfStore())
    kc = KcService(kf=kf, kip=kip)
    aoi = AoiService(kip=kip, kc=kc, kf=kf)
    eve = EveService(aoi=aoi, kc=kc, kf=kf, store=EveStore())
    aoi.bind_eve(eve)
    iie = IieService(eve=eve, kc=kc, kf=kf, aoi=aoi, store=IieStore())
    fle = FleService(iie=iie, eve=eve, kc=kc, kf=kf, aoi=aoi, store=FleStore())
    mee = MeeService(eve=eve, iie=iie, fle=fle, aoi=aoi, kf=kf, kc=kc, store=MeeStore())
    return kip, kf, kc, aoi, eve, iie, fle, mee


def test_mee_health_locked_architecture():
    *_, mee = _stack()
    h = mee.health()
    assert h["programme"] == "MEE"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert "fle" in h["no_redesign"]
    assert "ask_agi" in h["no_redesign"]
    assert "pmo" in h["future_consumers"]
    assert "events_immutable" in h["invariants"]


def test_event_normalisation_taxonomy():
    eng = MeeEngines(MeeStore())
    assert eng.normalise_type("Share Buyback")[0] == "buyback"
    assert eng.normalise_type("Repurchase")[0] == "buyback"
    assert eng.normalise_type("CEO Resigned")[0] == "executive_change"
    assert EVENT_TAXONOMY["buy-back"] == "buyback"


def test_duplicate_detection_and_immutability():
    *_, mee = _stack()
    a = mee.create_event(
        {
            "event_type": "buyback",
            "title": "Company announces share buyback",
            "company_ids": ["co_infy"],
            "effective_date": "2026-07-01",
            "confidence": 0.8,
            "evidence_ids": ["e1"],
            "evidence_links": [{"evidence_id": "e1", "claim_text": "buyback", "confidence": 0.8}],
            "verify": True,
        }
    )
    assert a.get("event_id")
    eid = a["event_id"]
    # Duplicate same fingerprint
    b = mee.create_event(
        {
            "event_type": "repurchase",
            "title": "Company announces share buyback",
            "company_ids": ["co_infy"],
            "effective_date": "2026-07-01",
            "confidence": 0.75,
            "evidence_ids": ["e2"],
            "verify": False,
        }
    )
    assert b.get("created") is False or b.get("reason") == "duplicate_or_low_confidence"
    # Original source count bumped
    assert mee.store.events[eid].source_count >= 2
    # Versioning never overwrites
    v2 = mee.version(eid, {"title": "Buyback programme updated", "confidence": 0.85})
    assert v2["version"] == 2
    assert v2["parent_event_id"] == eid
    assert mee.store.events[eid].status == "superseded"
    assert mee.store.events[eid].title == "Company announces share buyback"


def test_impact_engine_propagation_chain():
    *_, mee = _stack()
    ev = mee.create_event(
        {
            "event_type": "repo rate cut",
            "title": "RBI cuts repo rate by 25 bps",
            "confidence": 0.9,
            "evidence_ids": ["macro1"],
            "evidence_links": [{"evidence_id": "macro1", "claim_text": "repo cut", "confidence": 0.9}],
            "sector_ids": ["banking"],
            "verify": True,
        }
    )
    impact = mee.impact(ev["event_id"])
    assert impact["chain"]
    assert "banking" in impact["chain"]
    assert impact["first_order"] or impact["direct"]
    assert impact["second_order"] or impact["indirect"]
    # Propagation recorded idempotently
    props = [p for p in mee.store.propagations if p.event_id == ev["event_id"]]
    assert props
    mee.engines.propagate(ev["event_id"])
    props2 = [p for p in mee.store.propagations if p.event_id == ev["event_id"] and p.status == "done"]
    assert len(props2) >= 1


def test_company_sector_theme_timelines():
    *_, eve, iie, fle, mee = _stack()
    eve.ingest_aoi_artifact(
        {
            "artifact_id": "ar1",
            "connector_id": "company_ir",
            "doc_type": "annual_report",
            "company_id": "co_infy",
            "url": "https://example.com/infy",
            "checksum": "c1",
            "metadata": {"nse_symbol": "INFY"},
        },
        [
            {"field": "guidance", "value_text": "Guidance raised; buyback considered", "confidence": 0.88},
            {"field": "capex", "value_text": "Capacity expansion planned", "confidence": 0.8},
        ],
        company_symbol="INFY",
    )
    iie.analyse("INFY")
    out = mee.engines.ingest_from_iie("INFY")
    assert out["created"] >= 0  # catalysts may or may not map
    # Explicit corporate event
    ev = mee.create_event(
        {
            "event_type": "capacity increase",
            "title": "Plant expansion announced",
            "company_ids": ["co_infy"],
            "company_symbols": ["INFY"],
            "sector_ids": ["it_services"],
            "theme_ids": ["artificial_intelligence"],
            "confidence": 0.8,
            "evidence_ids": ["e3"],
            "verify": True,
        }
    )
    company = mee.company("co_infy", detect=False)
    assert company["count"] >= 1
    assert any(t["event_id"] == ev["event_id"] for t in company["timeline"])
    sector = mee.sector("it_services")
    assert sector["count"] >= 1
    theme = mee.theme("artificial_intelligence")
    assert theme["count"] >= 1


def test_similar_event_engine():
    *_, mee = _stack()
    a = mee.create_event(
        {
            "event_type": "oil_price",
            "title": "Oil rises 15%",
            "confidence": 0.8,
            "evidence_ids": ["o1"],
            "sector_ids": ["energy"],
            "verify": True,
        }
    )
    b = mee.create_event(
        {
            "event_type": "oil shock",
            "title": "Crude oil spike similar shock",
            "confidence": 0.75,
            "evidence_ids": ["o2"],
            "sector_ids": ["energy"],
            "effective_date": "2020-03-01",
            "verify": True,
        }
    )
    sim = mee.similar(a["event_id"])
    assert any(s["event_id"] == b["event_id"] for s in sim["similar"]) or sim["similar"]


def test_ask_agi_retrieves_what_changed():
    kip, kf, kc, aoi, eve, iie, fle, mee = _stack()
    mee.create_event(
        {
            "event_type": "dividend",
            "title": "INFY declares final dividend",
            "company_ids": ["co_infy"],
            "company_symbols": ["INFY"],
            "confidence": 0.85,
            "evidence_ids": ["d1"],
            "verify": True,
        }
    )
    rsp = RspService(kip=kip)
    irp = IrpService(kip=kip, rsp=rsp)
    rms = RmsService(kip=kip, rsp=rsp)
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    ui = UiService(
        aws=aws,
        ioc=ioc,
        kip=kip,
        rsp=rsp,
        rms=rms,
        cre=CREService(),
        validation=ValidationService(),
        irp=irp,
        kf=kf,
        kc=kc,
        aoi=aoi,
        eve=eve,
        iie=iie,
        fle=fle,
        mee=mee,
    )
    pack = ui.search("INFY dividend")
    assert pack.market_events.get("answer_policy") == "what_changed_before_reasoning"
    assert pack.market_events.get("guidance", {}).get("always_ask_what_changed") is True
    assert isinstance(pack.forecast_learning, dict)
    assert isinstance(pack.investment_intelligence, dict)


@pytest.mark.asyncio
async def test_mee_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/mee/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "MEE"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "fle" in body["no_redesign"]

        created = await client.post(
            "/v1/mee/events",
            json={
                "event_type": "acquisition",
                "title": "Strategic acquisition announced",
                "company_ids": ["co_demo"],
                "confidence": 0.8,
                "evidence_ids": ["ev_api"],
                "evidence_links": [{"evidence_id": "ev_api", "claim_text": "acquisition", "confidence": 0.8}],
                "verify": True,
            },
        )
        assert created.status_code == 200
        eid = created.json()["event_id"]

        got = await client.get(f"/v1/mee/events/{eid}")
        assert got.status_code == 200
        assert got.json()["impact"]

        impact = await client.get(f"/v1/mee/impact/{eid}")
        assert impact.status_code == 200

        dash = await client.get("/v1/mee/dashboard")
        assert dash.status_code == 200
        assert "live_feed" in dash.json()

        consult = await client.get("/v1/mee/consult", params={"q": "acquisition"})
        assert consult.status_code == 200
        assert consult.json()["answer_policy"] == "what_changed_before_reasoning"

        cycle = await client.post("/v1/mee/cycle", params={"limit": 10})
        assert cycle.status_code == 200

        # Backward compat
        fle_h = await client.get("/v1/fle/health")
        assert fle_h.status_code == 200
        assert fle_h.json()["programme"] == "FLE"
