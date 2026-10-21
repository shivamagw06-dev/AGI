"""CAE v1 — Context Assembly Engine orchestration gateway."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aoi.service import AoiService
from app.aws.service import AwsService
from app.cae.flags import CaeFlags
from app.cae.planner import classify_intents, plan_query
from app.cae.ranking import apply_token_budget, dedupe, score_item, assign_priority
from app.cae.models import RankedItem
from app.cae.service import CaeService
from app.cae.store import CaeStore
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
from app.mee.service import MeeService
from app.mee.store import MeeStore
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.ui.service import UiService
from app.validation.service import ValidationService


def _stack(*, cae_gateway: bool = True):
    kip = KipService()
    kf = KfService(kip=kip, store=KfStore())
    kc = KcService(kf=kf, kip=kip)
    aoi = AoiService(kip=kip, kc=kc, kf=kf)
    eve = EveService(aoi=aoi, kc=kc, kf=kf, store=EveStore())
    aoi.bind_eve(eve)
    iie = IieService(eve=eve, kc=kc, kf=kf, aoi=aoi, store=IieStore())
    fle = FleService(iie=iie, eve=eve, kc=kc, kf=kf, aoi=aoi, store=FleStore())
    mee = MeeService(eve=eve, iie=iie, fle=fle, aoi=aoi, kf=kf, kc=kc, store=MeeStore())
    flags = CaeFlags(
        cae=True,
        cae_cache=True,
        cae_compress=True,
        cae_parallel=False,  # deterministic in tests
        cae_ask_agi_gateway=cae_gateway,
    )
    cae = CaeService(
        flags=flags,
        store=CaeStore(),
        kf=kf,
        kc=kc,
        aoi=aoi,
        eve=eve,
        iie=iie,
        fle=fle,
        mee=mee,
    )
    return kip, kf, kc, aoi, eve, iie, fle, mee, cae


def _seed(eve, iie, fle, mee):
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
            {"field": "revenue", "value_text": "Revenue 125000 crore", "confidence": 0.9},
            {"field": "guidance", "value_text": "Guidance mid-single digit; buyback considered", "confidence": 0.85},
            {"field": "risks", "value_text": "Client concentration risk", "confidence": 0.8},
        ],
        company_symbol="INFY",
    )
    iie.analyse("INFY")
    fle.generate("INFY")
    mee.create_event(
        {
            "event_type": "buyback",
            "title": "INFY share buyback considered",
            "company_ids": ["co_infy"],
            "company_symbols": ["INFY"],
            "confidence": 0.85,
            "evidence_ids": ["e1"],
            "verify": True,
        }
    )


def test_cae_health_locked():
    *_, cae = _stack()
    h = cae.health()
    assert h["programme"] == "CAE"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["never_reasons"] is True
    assert "mee" in h["orchestrates"]
    assert "ask_agi" in h["no_redesign"]


def test_query_planning_and_intents():
    intents = classify_intents("Should I buy Tata Motors?")
    assert "company_research" in intents
    assert "investment_thesis" in intents
    plan = plan_query("Compare INFY vs TCS forecasts")
    assert "comparison" in plan.intents or "forecast" in plan.intents
    assert "iie" in plan.engines
    assert "fle" in plan.engines
    macro = plan_query("What is the impact of a repo rate cut?")
    assert "mee" in macro.engines or "fle" in macro.engines
    assert "kf" in macro.engines or "eve" in macro.engines


def test_ranking_dedupe_and_token_budget():
    items = [
        RankedItem(item_id="1", engine="eve", kind="evidence", title="Revenue", content={"v": 1}, confidence=0.9, dedupe_key="eve:rev"),
        RankedItem(item_id="2", engine="iie", kind="evidence", title="Revenue", content={"v": 1}, confidence=0.7, dedupe_key="iie:rev"),
        RankedItem(item_id="3", engine="aoi", kind="open_intelligence", title="Noise", content={"x": "y" * 500}, confidence=0.3, dedupe_key="aoi:n"),
    ]
    for it in items:
        score_item(it, query="INFY revenue", intents=["company_research"])
        assign_priority(it, intents=["company_research"])
    deduped, removed = dedupe(items)
    assert removed >= 1
    kept, usage, ratio = apply_token_budget(deduped, budget=200, compress=True)
    assert usage["total_estimate"] <= 200
    assert kept
    assert 0 < ratio <= 1


def test_context_assembly_and_cache():
    *_, eve, iie, fle, mee, cae = _stack()
    _seed(eve, iie, fle, mee)
    pkg = cae.context("Should I buy INFY?", use_cache=True)
    assert pkg["package_id"]
    assert pkg["plan"]["engines"]
    assert pkg["token_usage"]["total_estimate"] <= pkg["token_usage"]["budget"]
    assert pkg["explain"]
    assert pkg["soft_fields"]["context_assembly"]["answer_policy"] == "unified_context_before_reasoning"
    assert pkg["cache_hit"] is False
    # cache hit on second call
    pkg2 = cae.context("Should I buy INFY?", use_cache=True)
    assert pkg2["cache_hit"] is True
    assert cae.metrics()["metrics"]["cache_hits"] >= 1


def test_ask_agi_uses_single_cae_gateway():
    kip, kf, kc, aoi, eve, iie, fle, mee, cae = _stack()
    _seed(eve, iie, fle, mee)
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
        cae=cae,
    )
    pack = ui.search("What is the outlook for INFY?")
    assert pack.context_assembly.get("answer_policy") == "unified_context_before_reasoning"
    assert pack.context_assembly.get("guidance", {}).get("single_orchestration_call") is True
    assert isinstance(pack.evidence_verification, dict)
    assert isinstance(pack.investment_intelligence, dict)
    assert isinstance(pack.forecast_learning, dict)
    assert isinstance(pack.market_events, dict)


def test_ask_agi_falls_back_when_cae_disabled():
    kip, kf, kc, aoi, eve, iie, fle, mee, _ = _stack()
    _seed(eve, iie, fle, mee)
    # CAE unbound / disabled path
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
        cae=None,
    )
    pack = ui.search("INFY buyback event")
    # Fallback multi-engine still populates market_events
    assert pack.market_events.get("answer_policy") == "what_changed_before_reasoning"
    assert pack.context_assembly.get("guidance", {}).get("fallback_multi_engine") is True


@pytest.mark.asyncio
async def test_cae_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/cae/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "CAE"
        assert body["architecture_status"] == "v1.0.1 LOCKED"

        plan = await client.get("/v1/cae/query-plan", params={"q": "Should I buy INFY?"})
        assert plan.status_code == 200
        assert plan.json()["engines"]

        # Seed upstream then assemble
        await client.post(
            "/v1/aoi/run",
            params={"connector_id": "company_ir", "limit_per_connector": 6, "publish": True},
        )
        await client.post("/v1/iie/batch", params={"limit": 4})

        ctx = await client.get("/v1/cae/context", params={"q": "Should I buy INFY?", "use_cache": False})
        assert ctx.status_code == 200
        data = ctx.json()
        assert data["package_id"]
        assert "soft_fields" in data

        dash = await client.get("/v1/cae/dashboard")
        assert dash.status_code == 200

        metrics = await client.get("/v1/cae/metrics")
        assert metrics.status_code == 200

        # Backward compat
        mee_h = await client.get("/v1/mee/health")
        assert mee_h.status_code == 200
        assert mee_h.json()["programme"] == "MEE"
