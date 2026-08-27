"""IIE v1 — Investment Intelligence Engine after EVE / KCV / KF."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aoi.service import AoiService
from app.aws.service import AwsService
from app.cre.service import CREService
from app.eve.service import EveService
from app.eve.store import EveStore
from app.iie.config import DNA_DIMENSIONS, MACRO_IMPACT_MAP
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
    return kip, kf, kc, aoi, eve, iie


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
            {"field": "business_model", "value_text": "IT services and digital transformation", "confidence": 0.9},
            {"field": "revenue", "value_text": "Revenue 125000 crore", "confidence": 0.9},
            {"field": "margins", "value_text": "Operating margin 21%", "confidence": 0.85},
            {"field": "debt", "value_text": "Debt 2000 crore", "confidence": 0.8},
            {"field": "guidance", "value_text": "Guidance for mid-single digit growth", "confidence": 0.82},
            {"field": "risks", "value_text": "Client concentration and wage inflation risk", "confidence": 0.78},
            {"field": "opportunities", "value_text": "AI and cloud deal pipeline expanding", "confidence": 0.84},
            {"field": "capex", "value_text": "Capex for delivery centres", "confidence": 0.75},
            {"field": "management", "value_text": "Management reiterated capital discipline", "confidence": 0.8},
        ],
        company_symbol=symbol,
    )
    eve.ingest_aoi_artifact(
        {**base, "artifact_id": f"{symbol}_q", "doc_type": "quarterly_result", "checksum": f"{symbol}2"},
        [
            {"field": "revenue", "value_text": "Revenue 125000 crore", "confidence": 0.88},
            {"field": "products", "value_text": "AI platforms and semiconductor design services", "confidence": 0.8},
        ],
        company_symbol=symbol,
    )


def test_iie_health_and_locked_architecture():
    *_, iie = _stack()
    h = iie.health()
    assert h["programme"] == "IIE"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert "eve" in h["no_redesign"]
    assert "ask_agi" in h["no_redesign"]
    assert "raw_documents" in h["never_consumes"]


def test_company_profile_from_verified_evidence_only():
    *_, eve, iie = _stack()
    _seed_evidence(eve)
    result = iie.analyse("INFY")
    assert result["evidence_count"] >= 1
    profile = result["profile"]
    assert profile["company_id"]
    assert profile["explainability"]["responsible_engine"] == "iie.company_profile"
    assert profile["explainability"]["supporting_evidence"]
    assert profile["version"] == 1
    # DNA covers configured dimensions
    dna = result["dna"]
    assert set(dna["dimensions"].keys()) == set(DNA_DIMENSIONS)
    assert result["thesis"]["investment_thesis"]
    assert result["scenarios"]["bull"]["case_type"] == "bull"
    assert result["scenarios"]["base"]["case_type"] == "base"
    assert result["scenarios"]["bear"]["case_type"] == "bear"
    assert result["monitor"]["items"]


def test_knowledge_evolution_never_overwrites_history():
    *_, eve, iie = _stack()
    _seed_evidence(eve)
    first = iie.analyse("INFY")
    v1 = first["profile"]["version"]
    # Second analysis with new evidence
    eve.ingest_aoi_artifact(
        {
            "artifact_id": "infy_ar3",
            "connector_id": "company_ir",
            "doc_type": "annual_report",
            "company_id": "co_infy",
            "url": "https://example.com/infy3",
            "checksum": "infy3",
            "metadata": {"nse_symbol": "INFY"},
        },
        [{"field": "risks", "value_text": "Execution delays in large deals", "confidence": 0.86}],
        company_symbol="INFY",
    )
    second = iie.analyse("INFY")
    assert second["profile"]["version"] == v1 + 1
    evo = iie.evolution(entity_id=second["company_id"])
    assert evo["count"] >= 1
    # Historical payload retained
    assert any(h.get("superseded") for h in evo["history"])


def test_risk_and_catalyst_engines():
    *_, eve, iie = _stack()
    _seed_evidence(eve)
    result = iie.analyse("INFY")
    cid = result["company_id"]
    risks = iie.risks(company_id=cid)
    assert risks["count"] >= 1
    assert all(r.get("explainability", {}).get("supporting_evidence") is not None for r in risks["risks"])
    cats = iie.catalysts(company_id=cid)
    assert cats["count"] >= 1
    opps = iie.opportunities(company_id=cid)
    assert opps["count"] >= 1


def test_scenario_engine_probabilities_sum_near_one():
    *_, eve, iie = _stack()
    _seed_evidence(eve)
    scn = iie.scenario("INFY")["scenarios"]
    total = float(scn["bull"]["probability"]) + float(scn["base"]["probability"]) + float(scn["bear"]["probability"])
    assert abs(total - 1.0) < 1e-6
    assert scn["explainability"]["responsible_engine"] == "iie.scenario"


def test_macro_and_theme_sector_intelligence():
    *_, eve, iie = _stack()
    _seed_evidence(eve)
    result = iie.analyse("INFY")
    cid = result["company_id"]
    sectors = iie.list_sectors()
    assert sectors["count"] >= 1
    themes = iie.list_themes()
    assert themes["count"] >= 1
    # AI keyword from products evidence should classify theme
    theme_ids = {t["theme_id"] for t in themes["themes"] if cid in (t.get("company_ids") or [])}
    assert "artificial_intelligence" in theme_ids or "semiconductors" in theme_ids
    macro = iie.macro("repo_rate_cut")
    assert macro["chain"] == MACRO_IMPACT_MAP["repo_rate_cut"]
    assert macro["direct_impacts"] or macro["indirect_impacts"]


def test_compare_engine():
    *_, eve, iie = _stack()
    _seed_evidence(eve, company_id="co_infy", symbol="INFY")
    _seed_evidence(eve, company_id="co_tcs", symbol="TCS")
    a = iie.analyse("INFY")
    b = iie.analyse("TCS")
    cmp = iie.compare([a["company_id"], b["company_id"]])
    assert cmp["comparison_id"]
    assert a["company_id"] in cmp["matrix"]
    assert b["company_id"] in cmp["matrix"]
    assert "moat" in cmp["dimensions"] or "pricing_power" in cmp["dimensions"]


def test_ask_agi_retrieves_investment_intelligence_before_reasoning():
    kip, kf, kc, aoi, eve, iie = _stack()
    _seed_evidence(eve)
    iie.analyse("INFY")
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
    )
    pack = ui.search("INFY AI opportunities")
    assert pack.investment_intelligence.get("answer_policy") == "investment_intelligence_before_reasoning"
    assert pack.investment_intelligence.get("guidance", {}).get("never_hallucinate") is True
    # Backward compatible soft fields remain
    assert isinstance(pack.evidence_verification, dict)
    assert isinstance(pack.open_intelligence, dict)
    assert isinstance(pack.knowledge_corpus, dict)


@pytest.mark.asyncio
async def test_iie_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/iie/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "IIE"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "eve" in body["no_redesign"]

        # Seed via AOI → EVE, then analyse
        run = await client.post(
            "/v1/aoi/run",
            params={"connector_id": "company_ir", "limit_per_connector": 8, "publish": True},
        )
        assert run.status_code == 200

        batch = await client.post("/v1/iie/batch", params={"limit": 8})
        assert batch.status_code == 200

        dash = await client.get("/v1/iie/dashboard")
        assert dash.status_code == 200
        assert "metrics" in dash.json()
        assert "confidence_heatmap" in dash.json()

        sectors = await client.get("/v1/iie/sector")
        assert sectors.status_code == 200

        themes = await client.get("/v1/iie/theme")
        assert themes.status_code == 200

        macro = await client.get("/v1/iie/macro", params={"event": "repo_rate_cut"})
        assert macro.status_code == 200
        assert macro.json()["chain"]

        consult = await client.get("/v1/iie/consult", params={"q": "INFY"})
        assert consult.status_code == 200
        assert consult.json()["answer_policy"] == "investment_intelligence_before_reasoning"

        search = await client.get("/v1/iie/search", params={"q": "IT"})
        assert search.status_code == 200

        # Eve health still works (backward compat)
        eve_h = await client.get("/v1/eve/health")
        assert eve_h.status_code == 200
        assert eve_h.json()["programme"] == "EVE"
