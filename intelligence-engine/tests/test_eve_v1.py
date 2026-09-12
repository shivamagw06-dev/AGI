"""EVE v1 — Evidence & Verification Engine between AOI and KCV/KF."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aoi.service import AoiService
from app.aws.service import AwsService
from app.cre.service import CREService
from app.eve.config import SOURCE_RELIABILITY
from app.eve.confidence import score_confidence
from app.eve.models import EvidenceObject, Provenance
from app.eve.normalise import canonical_fact_key, values_equivalent
from app.eve.service import EveService
from app.eve.store import EveStore
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
    return kip, kf, kc, aoi, eve


def test_source_reliability_is_configurable_not_hardcoded():
    assert SOURCE_RELIABILITY["annual_report"] == 1.0
    assert SOURCE_RELIABILITY["broker_research"] == 0.8
    assert SOURCE_RELIABILITY["unknown"] == 0.3
    conf = score_confidence(
        source_reliability=1.0,
        supporting_sources=3,
        document_freshness=1.0,
        consistency=1.0,
        historical_stability=1.0,
        parser_confidence=1.0,
        extraction_quality=1.0,
        recency=1.0,
    )
    assert 0.7 <= conf <= 0.995


def test_fact_normalisation_and_equivalence():
    assert canonical_fact_key("Net Profit") == "pat"
    assert canonical_fact_key("Profit After Tax") == "pat"
    assert canonical_fact_key("Turnover") == "revenue"
    assert values_equivalent("₹100 Crore", "100 crore")
    assert not values_equivalent("₹100 Crore", "₹50 Crore")


def test_conflict_detection_preserves_both_sides():
    _, _, _, _, eve = _stack()
    art = {
        "artifact_id": "doc_a",
        "connector_id": "company_ir",
        "doc_type": "annual_report",
        "company_id": "co_infy",
        "url": "https://example.com/ar",
        "checksum": "abc123",
        "metadata": {"nse_symbol": "INFY"},
    }
    eve.ingest_aoi_artifact(
        art,
        [{"field": "debt", "value_text": "Debt 50000 crore", "confidence": 0.9, "section": "Balance Sheet"}],
        company_symbol="INFY",
    )
    eve.ingest_aoi_artifact(
        {
            **art,
            "artifact_id": "doc_b",
            "doc_type": "press_release",
            "connector_id": "company_ir",
            "checksum": "def456",
        },
        [{"field": "debt", "value_text": "Debt 48000 crore", "confidence": 0.7, "section": "PR"}],
        company_symbol="INFY",
    )
    conflicts = eve.conflicts()
    assert conflicts["count"] >= 1
    # Both evidence records remain
    ev = eve.list_evidence(company_id="co_infy", fact_key="debt")
    assert ev["count"] >= 2
    statuses = {e["verification_status"] for e in ev["evidence"]}
    assert "conflicted" in statuses


def test_versioning_and_multi_source_raises_confidence():
    _, _, _, _, eve = _stack()
    base = {
        "connector_id": "company_ir",
        "company_id": "co_tcs",
        "url": "https://example.com/tcs",
        "metadata": {"nse_symbol": "TCS"},
    }
    eve.ingest_aoi_artifact(
        {**base, "artifact_id": "ar1", "doc_type": "annual_report", "checksum": "c1"},
        [{"field": "revenue", "value_text": "Revenue 125000 crore", "confidence": 0.9}],
        company_symbol="TCS",
    )
    eve.ingest_aoi_artifact(
        {**base, "artifact_id": "q1", "doc_type": "quarterly_result", "checksum": "c2"},
        [{"field": "Sales", "value_text": "Revenue 125000 crore", "confidence": 0.88}],
        company_symbol="TCS",
    )
    pack = eve.company_pack("TCS")
    assert pack["health"]["evidence_count"] >= 2
    # Confirming sources should verify at least one record
    statuses = {e["verification_status"] for e in pack["evidence"]}
    assert "verified" in statuses or pack["health"]["average_confidence"] > 0.5

    # Material change creates version history
    eve.ingest_aoi_artifact(
        {**base, "artifact_id": "ar2", "doc_type": "annual_report", "checksum": "c3"},
        [{"field": "revenue", "value_text": "Revenue 140000 crore", "confidence": 0.91}],
        company_symbol="TCS",
    )
    assert any(v.fact_key == "revenue" for v in eve.store.versions)


def test_aoi_publish_soft_gates_through_eve_and_timeline():
    _, _, _, aoi, eve = _stack()
    result = aoi.run_cycle(connector_ids=["company_ir", "rbi"], limit_per_connector=12, publish=True)
    assert result["totals"]["published"] >= 1
    assert eve.store.metrics.evidence_count >= 1
    dash = eve.dashboard()
    assert dash["programme"] == "EVE"
    assert dash["architecture_status"] == "v1.0.1 LOCKED"
    assert dash["sources"]
    # Timeline and/or verification artifacts exist after ingest
    assert dash["metrics"]["evidence_count"] >= 1


def test_ask_agi_uses_eve_evidence_consult():
    kip, kf, kc, aoi, eve = _stack()
    aoi.run_cycle(connector_ids=["company_ir"], limit_per_connector=10, publish=True)
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
    )
    pack = ui.search("Adani")
    assert pack.evidence_verification.get("answer_policy") == "verified_evidence_before_raw_facts"
    assert pack.evidence_verification.get("guidance", {}).get("avoid_hallucinated_certainty") is True
    # Backward compatible fields remain
    assert isinstance(pack.open_intelligence, dict)
    assert isinstance(pack.knowledge_corpus, dict)


def test_daily_verification_jobs_and_soft_delete():
    _, _, _, _, eve = _stack()
    eve.ingest_aoi_artifact(
        {
            "artifact_id": "x1",
            "connector_id": "nse",
            "doc_type": "announcements",
            "company_id": "co_infy",
            "url": "https://example-ir.invalid/broken",
            "checksum": "z1",
            "metadata": {"nse_symbol": "INFY"},
        },
        [{"field": "guidance", "value_text": "Guidance cautious for FY27", "confidence": 0.8}],
        company_symbol="INFY",
    )
    out = eve.run_verification_jobs()
    assert out["ran_at"]
    assert out["tasks_open"] >= 1
    eid = next(iter(eve.store.evidence))
    assert eve.store.soft_delete_evidence(eid) is True
    assert eve.store.evidence[eid].soft_deleted is True
    # Soft-deleted excluded from active list
    assert all(e.evidence_id != eid for e in eve.store.active_evidence())


@pytest.mark.asyncio
async def test_eve_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/eve/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "EVE"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "aoi" in body["no_redesign"]

        # Seed evidence via AOI run (wired with EVE)
        run = await client.post(
            "/v1/aoi/run",
            params={"connector_id": "company_ir", "limit_per_connector": 8, "publish": True},
        )
        assert run.status_code == 200

        dash = await client.get("/v1/eve/dashboard")
        assert dash.status_code == 200
        assert "metrics" in dash.json()

        sources = await client.get("/v1/eve/source")
        assert sources.status_code == 200
        assert sources.json()["count"] >= 1

        evidence = await client.get("/v1/eve/evidence", params={"limit": 20})
        assert evidence.status_code == 200

        trust = await client.get("/v1/eve/trust")
        assert trust.status_code == 200

        consult = await client.get("/v1/eve/consult", params={"q": "INFY"})
        assert consult.status_code == 200
        assert consult.json()["answer_policy"] == "verified_evidence_before_raw_facts"

        jobs = await client.post("/v1/eve/verification/run")
        assert jobs.status_code == 200
