"""FLE v1 — Forecasting & Learning Engine after IIE."""

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
    return kip, kf, kc, aoi, eve, iie, fle


def _seed_evidence(eve: EveService, *, company_id: str = "co_infy", symbol: str = "INFY") -> None:
    base = {
        "connector_id": "company_ir",
        "company_id": company_id,
        "url": f"https://example.com/{symbol.lower()}",
        "metadata": {"nse_symbol": symbol},
    }
    eve.ingest_aoi_artifact(
        {**base, "artifact_id": f"{symbol}_ar", "doc_type": "annual_report", "checksum": f"{symbol}1"},
        [
            {"field": "revenue", "value_text": "Revenue 125000 crore", "confidence": 0.9},
            {"field": "margins", "value_text": "Operating margin 21%", "confidence": 0.85},
            {"field": "guidance", "value_text": "Guidance for mid-single digit growth", "confidence": 0.82},
            {"field": "risks", "value_text": "Client concentration risk", "confidence": 0.78},
            {"field": "opportunities", "value_text": "AI deal pipeline expanding", "confidence": 0.84},
            {"field": "business_model", "value_text": "IT services and digital transformation", "confidence": 0.9},
        ],
        company_symbol=symbol,
    )


def test_fle_health_locked_architecture():
    *_, fle = _stack()
    h = fle.health()
    assert h["programme"] == "FLE"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert "iie" in h["no_redesign"]
    assert "ask_agi" in h["no_redesign"]
    assert "forecasts_immutable" in h["invariants"]


def test_forecast_requires_assumptions_and_evidence():
    *_, fle = _stack()
    with pytest.raises(ValueError, match="assumptions"):
        fle.create_forecast(
            {
                "metric": "revenue",
                "predicted_value": "130000",
                "evidence_ids": ["ev1"],
            }
        )
    with pytest.raises(ValueError, match="evidence"):
        fle.create_forecast(
            {
                "metric": "revenue",
                "predicted_value": "130000",
                "assumptions": ["Demand stable"],
            }
        )


def test_create_forecast_immutable_and_versioned():
    *_, eve, iie, fle = _stack()
    _seed_evidence(eve)
    iie.analyse("INFY")
    fc = fle.create_forecast(
        {
            "metric": "revenue",
            "predicted_value": "130000 crore",
            "predicted_numeric": 130000,
            "company_id": "co_infy",
            "company_symbol": "INFY",
            "direction": "up",
            "confidence": 0.8,
            "assumptions": ["IT services demand stable", "No major FX shock"],
            "evidence_ids": ["ev_seed_1"],
            "evidence_links": [{"evidence_id": "ev_seed_1", "claim_text": "Revenue 125000", "confidence": 0.9}],
            "why": "Growth continuation from verified revenue evidence",
            "origin": "user_request",
        }
    )
    assert fc["forecast_id"]
    assert fc["version"] == 1
    assert fc["assumptions"]
    assert fc["bull"]["case_type"] == "bull"
    assert fc["explainability"]["responsible_engine"] == "fle.forecast"

    # Immutability: same id not overwritten
    fid = fc["forecast_id"]
    fle.store.add_forecast(fle.store.forecasts[fid])  # no-op
    assert fle.store.forecasts[fid].predicted_value == "130000 crore"

    v2 = fle.version(fid, {"predicted_value": "135000 crore", "predicted_numeric": 135000, "confidence": 0.75})
    assert v2["version"] == 2
    assert v2["parent_forecast_id"] == fid
    assert fle.store.forecasts[fid].status == "superseded"
    assert fle.store.forecasts[v2["forecast_id"]].predicted_value == "135000 crore"


def test_resolution_accuracy_and_learning():
    *_, eve, iie, fle = _stack()
    _seed_evidence(eve)
    iie.analyse("INFY")
    fc = fle.create_forecast(
        {
            "metric": "revenue",
            "predicted_value": "130000",
            "predicted_numeric": 130000,
            "company_id": "co_infy",
            "direction": "up",
            "confidence": 0.9,
            "assumptions": ["Demand recovery", "Pricing stable"],
            "evidence_ids": ["e1"],
            "evidence_links": [{"evidence_id": "e1", "claim_text": "rev", "confidence": 0.9}],
        }
    )
    out = fle.resolve(fc["forecast_id"], {"actual_value": "132000", "actual_numeric": 132000})
    assert out["already_resolved"] is False
    assert out["outcome"]["direction_correct"] is True
    assert out["outcome"]["accuracy_score"] > 0.5
    assert out["learning"]["lessons_learned"]
    assert out["learning"]["learning_id"]

    # Second resolve is idempotent
    out2 = fle.resolve(fc["forecast_id"], {"actual_value": "999"})
    assert out2["already_resolved"] is True

    acc = fle.accuracy(scope="global", scope_id="all")
    assert acc["accuracy"]["resolved_count"] >= 1
    cal = fle.calibration()
    assert cal["current"]["buckets"]
    learn = fle.learning(company_id="co_infy")
    assert learn["count"] >= 1


def test_calibration_detects_overconfidence():
    *_, fle = _stack()
    # Create several high-confidence wrong forecasts
    for i in range(3):
        fc = fle.create_forecast(
            {
                "metric": "eps",
                "predicted_value": str(100 + i),
                "predicted_numeric": 100 + i,
                "company_id": f"co_{i}",
                "direction": "up",
                "confidence": 0.92,
                "assumptions": ["Stable margins"],
                "evidence_ids": [f"e{i}"],
                "evidence_links": [{"evidence_id": f"e{i}", "claim_text": "x", "confidence": 0.9}],
            }
        )
        fle.resolve(fc["forecast_id"], {"actual_value": "50", "actual_numeric": 50})
    cal = fle.calibration()["current"]
    very_high = next(b for b in cal["buckets"] if b["band"] == "very_high")
    assert very_high["forecast_count"] >= 3
    assert very_high["calibration_label"] in {"overconfident", "well_calibrated", "underconfident"}
    # Drift should reflect confidence vs success gap
    assert isinstance(cal["calibration_drift"], float)


def test_scenario_framework_on_forecast():
    *_, fle = _stack()
    fc = fle.create_forecast(
        {
            "metric": "margins",
            "predicted_value": "22%",
            "company_id": "co_infy",
            "assumptions": ["Wage inflation contained"],
            "evidence_ids": ["e1"],
            "evidence_links": [{"evidence_id": "e1", "claim_text": "margins", "confidence": 0.8}],
            "confidence": 0.7,
        }
    )
    scn = fle.scenarios(fc["forecast_id"])
    total = scn["bull"]["probability"] + scn["base"]["probability"] + scn["bear"]["probability"]
    assert abs(total - 1.0) < 1e-6


def test_generate_from_iie_and_company_timeline():
    *_, eve, iie, fle = _stack()
    _seed_evidence(eve)
    iie.analyse("INFY")
    gen = fle.generate("INFY")
    assert gen["created"] >= 1
    pack = fle.company("INFY", generate_if_empty=False)
    assert pack["company_id"]
    assert pack["historical_forecasts"]
    assert pack["health"]["forecast_coverage"] >= 1


def test_ask_agi_retrieves_forecast_learning_before_reasoning():
    kip, kf, kc, aoi, eve, iie, fle = _stack()
    _seed_evidence(eve)
    iie.analyse("INFY")
    fle.generate("INFY")
    # Resolve one to create learning + calibration signal
    fcs = fle.list_forecasts(company_id="co_infy")["forecasts"]
    if fcs:
        fle.resolve(
            fcs[0]["forecast_id"],
            {"actual_value": "1", "actual_numeric": 1, "notes": "test"},
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
    )
    pack = ui.search("INFY revenue outlook")
    assert pack.forecast_learning.get("answer_policy") == "forecast_history_and_calibration_before_reasoning"
    assert pack.forecast_learning.get("guidance", {}).get("never_forget_predictions") is True
    # Backward compatible soft fields remain
    assert isinstance(pack.investment_intelligence, dict)
    assert isinstance(pack.evidence_verification, dict)


@pytest.mark.asyncio
async def test_fle_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/fle/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "FLE"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "iie" in body["no_redesign"]

        # Seed AOI→EVE→IIE then generate forecasts
        run = await client.post(
            "/v1/aoi/run",
            params={"connector_id": "company_ir", "limit_per_connector": 8, "publish": True},
        )
        assert run.status_code == 200
        await client.post("/v1/iie/batch", params={"limit": 6})

        created = await client.post(
            "/v1/fle/forecast",
            json={
                "metric": "revenue",
                "predicted_value": "140000",
                "predicted_numeric": 140000,
                "company_id": "co_demo",
                "direction": "up",
                "confidence": 0.7,
                "assumptions": ["Demand holds", "FX stable"],
                "evidence_ids": ["ev_api_1"],
                "evidence_links": [{"evidence_id": "ev_api_1", "claim_text": "demo", "confidence": 0.7}],
            },
        )
        assert created.status_code == 200
        fid = created.json()["forecast_id"]

        got = await client.get(f"/v1/fle/forecast/{fid}")
        assert got.status_code == 200

        resolved = await client.post(
            f"/v1/fle/forecast/{fid}/resolve",
            json={"actual_value": "141000", "actual_numeric": 141000},
        )
        assert resolved.status_code == 200
        assert resolved.json()["outcome"]["accuracy_score"] >= 0

        dash = await client.get("/v1/fle/dashboard")
        assert dash.status_code == 200
        assert "metrics" in dash.json()

        cal = await client.get("/v1/fle/calibration")
        assert cal.status_code == 200

        learn = await client.get("/v1/fle/learning")
        assert learn.status_code == 200

        consult = await client.get("/v1/fle/consult", params={"q": "INFY"})
        assert consult.status_code == 200
        assert consult.json()["answer_policy"] == "forecast_history_and_calibration_before_reasoning"

        # Backward compat: IIE still healthy
        iie_h = await client.get("/v1/iie/health")
        assert iie_h.status_code == 200
        assert iie_h.json()["programme"] == "IIE"
