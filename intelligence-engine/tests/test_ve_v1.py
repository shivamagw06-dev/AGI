"""VE v1 — Valuation Engine institutional intrinsic value platform."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aoi.service import AoiService
from app.eve.service import EveService
from app.eve.store import EveStore
from app.fle.service import FleService
from app.fle.store import FleStore
from app.iie.service import IieService
from app.iie.store import IieStore
from app.kc.service import KcService
from app.kf.service import KfService
from app.kf.store import KfStore
from app.kip.service import KipService
from app.main import app
from app.mee.service import MeeService
from app.mee.store import MeeStore
from app.ui.service import UiService
from app.ve.config import SUPPORTED_MODELS
from app.ve.engines import MODEL_PLUGINS, dcf_fcff, relative_pe
from app.ve.flags import VeFlags
from app.ve.service import VeService
from app.ve.store import VeStore


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
    ve = VeService(
        flags=VeFlags(
            ve=True,
            ve_auto_value=True,
            ve_scenarios=True,
            ve_sensitivity=True,
            ve_relative=True,
            ve_ibus_updates=True,
        ),
        store=VeStore(),
        eve=eve,
        iie=iie,
        fle=fle,
        mee=mee,
        aoi=aoi,
    )
    return kip, kf, kc, aoi, eve, iie, fle, mee, ve


def _seed(eve, iie, fle, mee):
    eve.ingest_aoi_artifact(
        {
            "artifact_id": "ar_ve1",
            "connector_id": "company_ir",
            "doc_type": "annual_report",
            "company_id": "co_infy",
            "url": "https://example.com/infy-ve",
            "checksum": "cve1",
            "metadata": {"nse_symbol": "INFY"},
        },
        [
            {"field": "revenue", "value_text": "Revenue 150000 crore", "confidence": 0.9},
            {"field": "guidance", "value_text": "Guidance mid-single digit growth", "confidence": 0.85},
            {"field": "risks", "value_text": "Client concentration risk", "confidence": 0.8},
        ],
        company_symbol="INFY",
    )
    iie.analyse("INFY")
    fle.generate("INFY")
    mee.create_event(
        {
            "event_type": "buyback",
            "title": "INFY buyback considered",
            "company_ids": ["co_infy"],
            "company_symbols": ["INFY"],
            "confidence": 0.85,
            "evidence_ids": ["e1"],
            "verify": True,
        }
    )


def test_ve_health_locked():
    *_, ve = _stack()
    h = ve.health()
    assert h["programme"] == "VE"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["never_executes_trades"] is True
    assert h["never_consumes_raw_documents"] is True
    assert "cae" in h["no_redesign"]
    assert "ib" in h["no_redesign"]
    assert set(SUPPORTED_MODELS).issubset(set(h["models"]))


def test_model_plugins_cover_required_methods():
    for name in SUPPORTED_MODELS:
        assert name in MODEL_PLUGINS
    assumptions = {
        "revenue_growth": 0.12,
        "ebit_margin": 0.22,
        "tax_rate": 0.25,
        "capex_pct_sales": 0.04,
        "nwc_pct_sales": 0.08,
        "wacc": 0.11,
        "cost_of_equity": 0.13,
        "terminal_growth": 0.04,
        "shares_outstanding_cr": 400.0,
        "net_debt_cr": 0.0,
        "book_equity_cr": 80000.0,
        "roe": 0.18,
        "dividend_payout": 0.4,
        "tangible_assets_cr": 50000.0,
        "replacement_premium": 1.15,
    }
    dcf = dcf_fcff(assumptions)
    assert dcf.intrinsic_value > 0
    pe = relative_pe(assumptions, peer_pe=24.0)
    assert pe.intrinsic_value > 0


def test_value_company_versioned_history_and_scenarios():
    *_, eve, iie, fle, mee, ve = _stack()
    _seed(eve, iie, fle, mee)
    first = ve.value("INFY", trigger="test")
    v1 = first["valuation"]
    assert v1["version"] == 1
    assert v1["intrinsic_value"] > 0
    assert v1["margin_of_safety"]
    assert len(v1["scenarios"]) == 3
    assert {s["name"] for s in v1["scenarios"]} == {"bull", "base", "bear"}
    assert v1["assumptions"]
    assert all("source" in a and "confidence" in a for a in v1["assumptions"])
    assert v1["explainability"].get("why")
    second = ve.value("INFY", trigger="test_recalc")
    v2 = second["valuation"]
    assert v2["version"] == 2
    assert v2["parent_valuation_id"] == v1["valuation_id"]
    # Never overwrite — both ids present
    assert ve.store.get(v1["valuation_id"]) is not None
    assert ve.store.get(v1["valuation_id"]).superseded is True
    hist = ve.history("INFY")
    assert hist["count"] == 2


def test_margin_of_safety_and_sensitivity():
    *_, eve, iie, fle, mee, ve = _stack()
    _seed(eve, iie, fle, mee)
    ve.value("INFY", market_price=5000.0)
    mos_pack = ve.company("INFY")
    mos = (mos_pack["latest"] or {}).get("margin_of_safety") or {}
    assert "discount_premium_pct" in mos
    assert "suggested_mos_pct" in mos
    sens = ve.sensitivity("INFY")
    assert sens["sensitivity"]
    assert sens["most_sensitive_assumptions"]


def test_compare_and_model_api():
    *_, eve, iie, fle, mee, ve = _stack()
    _seed(eve, iie, fle, mee)
    cmp = ve.compare("INFY", peers=["TCS", "WIPRO"])
    assert cmp["peers"]
    assert "pe" in cmp["metrics"]
    model = ve.model("dcf_fcff", "INFY")
    assert model["model"] == "dcf_fcff"
    assert model["intrinsic_value"] > 0


def test_consult_ask_agi_and_ui_soft_field():
    *_, eve, iie, fle, mee, ve = _stack()
    _seed(eve, iie, fle, mee)
    consult = ve.consult("Is INFY undervalued?")
    assert consult["answer_policy"] == "valuation_before_reasoning"
    assert consult["latest_valuation"]
    assert "is_undervalued" in consult["questions"]
    ui = UiService(ve=ve, cae=None)
    view = ui.search("What is INFY intrinsic value?", ticker="INFY")
    assert isinstance(view.valuation, dict)
    assert view.valuation.get("answer_policy") == "valuation_before_reasoning"
    assert view.valuation.get("latest_valuation") or view.valuation.get("company")


def test_disabled_ve_fallback():
    ve = VeService(flags=VeFlags(ve=False), store=VeStore())
    assert ve.health()["status"] == "disabled"
    with pytest.raises(RuntimeError, match="VE is disabled"):
        ve.value("INFY")
    ui = UiService(ve=None)
    view = ui.search("INFY valuation")
    assert isinstance(view.valuation, dict)


def test_bus_event_recalculation():
    *_, eve, iie, fle, mee, ve = _stack()
    _seed(eve, iie, fle, mee)
    ve.value("INFY")
    before = ve.store.metrics.valuations_created

    class Evt:
        payload = {"company_symbol": "INFY"}
        aggregate_id = "INFY"

    ve.on_bus_event(Evt())
    assert ve.store.metrics.valuations_created > before
    assert ve.store.metrics.bus_triggered >= 1


@pytest.mark.asyncio
async def test_ve_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/v1/ve/health")
        assert h.status_code == 200
        assert h.json()["programme"] == "VE"
        d = await client.get("/v1/ve/dashboard")
        assert d.status_code == 200
        valued = await client.post("/v1/ve/value", json={"key": "INFY", "trigger": "api_test"})
        assert valued.status_code == 200
        assert valued.json()["valuation"]["intrinsic_value"] > 0
        company = await client.get("/v1/ve/company/INFY")
        assert company.status_code == 200
        scenarios = await client.get("/v1/ve/scenarios", params={"key": "INFY"})
        assert scenarios.status_code == 200
        assert len(scenarios.json()["scenarios"]) == 3
        compare = await client.get("/v1/ve/compare", params={"key": "INFY"})
        assert compare.status_code == 200
        sens = await client.get("/v1/ve/sensitivity", params={"key": "INFY"})
        assert sens.status_code == 200
        consult = await client.get("/v1/ve/consult", params={"q": "INFY undervalued?"})
        assert consult.status_code == 200
        # Locked engines remain healthy
        assert (await client.get("/v1/ib/health")).json()["programme"] == "IB"
        assert (await client.get("/v1/cae/health")).json()["programme"] == "CAE"
        assert (await client.get("/v1/fle/health")).json()["programme"] == "FLE"
