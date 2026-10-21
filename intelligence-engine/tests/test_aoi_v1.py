"""AOI v1 — Open Intelligence acquisition without redesigning locked cores."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aoi.connectors.factory import build_connectors, list_optional_connectors, register_connector
from app.aoi.connector import SourceConnector
from app.aoi.flags import AoiFlags
from app.aoi.models import DocumentArtifact
from app.aoi.parsers import detect_format, parse_artifact
from app.aoi.registry import CompanyRegistry
from app.aoi.service import AoiService
from app.aoi.store import AoiStore
from app.aws.service import AwsService
from app.cre.service import CREService
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


def test_registry_canonical_identity_and_aliases():
    reg = CompanyRegistry()
    stats = reg.seed_default_universes()
    assert stats["nifty_50"] == 50
    ril = reg.resolve("RIL")
    assert ril is not None
    assert ril.nse_symbol == "RELIANCE"
    assert reg.resolve("Reliance Industries") is not None
    assert reg.by_symbol("INFY").company_name.startswith("Infosys")
    # Never duplicate on re-seed
    before = len(list(reg.all()))
    reg.seed_default_universes()
    assert len(list(reg.all())) == before


def test_connectors_are_pluggable_and_independent():
    flags = AoiFlags(aoi=True, aoi_live_fetch=False)
    connectors = build_connectors(flags)
    assert "company_ir" in connectors
    assert "nse" in connectors
    assert "rbi" in connectors
    assert "fred" in connectors
    optional = list_optional_connectors()
    assert any(o["connector_id"] == "openstreetmap" for o in optional)

    class DummyConnector(SourceConnector):
        connector_id = "dummy_test"
        name = "Dummy"

        def discover(self, registry):
            return []

    register_connector("dummy_test", DummyConnector)
    flags2 = AoiFlags(aoi=True)
    # custom registration available for future builds
    assert "dummy_test" in __import__("app.aoi.connectors.factory", fromlist=["_BUILDERS"])._BUILDERS


def test_parser_detects_formats_and_pipeline_is_idempotent():
    art = DocumentArtifact(
        connector_id="fred",
        title="series",
        url="https://example.com/data.json",
        content_text='{"series_id":"DFF","value":"5.25"}',
        format="unknown",
    )
    assert detect_format(art) == "json"
    parsed = parse_artifact(art)
    assert parsed.format == "json"
    assert parsed.status == "parsed"

    kip = KipService()
    kf = KfService(kip=kip, store=KfStore())
    kc = KcService(kf=kf, kip=kip)
    aoi = AoiService(kip=kip, kc=kc, kf=kf, store=AoiStore())
    first = aoi.run_cycle(connector_ids=["rbi", "fred"], limit_per_connector=10, publish=False)
    assert first["totals"]["discovered"] >= 1
    checksums = set(aoi.store.known_checksums())
    arts_before = len(aoi.store.artifacts)
    second = aoi.run_cycle(connector_ids=["rbi", "fred"], limit_per_connector=10, publish=False)
    # Unchanged files are not re-created; artifact count stays stable once fully ingested.
    assert second["totals"]["downloaded"] == 0
    assert len(aoi.store.artifacts) == arts_before
    assert checksums == aoi.store.known_checksums()


def test_acquisition_builds_nifty50_profiles_versions_quality_gaps():
    kip = KipService()
    kf = KfService(kip=kip, store=KfStore())
    kc = KcService(kf=kf, kip=kip)
    aoi = AoiService(kip=kip, kc=kc, kf=kf)
    result = aoi.run_cycle(
        connector_ids=["company_ir", "nse", "rbi"],
        limit_per_connector=40,
        publish=True,
    )
    assert result["registry"]["nifty_50"] == 50
    assert result["totals"]["extracted_facts"] >= 1
    assert result["coverage"]["artifacts"] >= 1

    dash = aoi.dashboard()
    assert dash["programme"] == "AOI"
    assert dash["architecture_status"] == "v1.0.1 LOCKED"
    assert dash["quality_heatmap"]
    assert dash["learning"]
    assert "gaps" in dash

    # Registry is sorted alphabetically — ADANIENT is in the first IR batch.
    company = aoi.get_company("ADANIENT")
    assert company["company"]["nse_symbol"] == "ADANIENT"
    assert company["documents"] or company["latest_facts"]
    assert isinstance(company["versions"], list)

    search = aoi.search("Adani guidance")
    assert search["count"] >= 1
    consult = aoi.consult("RIL")
    assert consult["answer_policy"] == "aoi_then_kc_kf_then_documents"
    assert consult["company"]["company"]["nse_symbol"] == "RELIANCE"


def test_ask_agi_soft_uses_aoi_without_breaking_corpus():
    kip = KipService()
    kf = KfService(kip=kip, store=KfStore())
    kc = KcService(kf=kf, kip=kip)
    aoi = AoiService(kip=kip, kc=kc, kf=kf)
    aoi.run_cycle(connector_ids=["company_ir"], limit_per_connector=12, publish=False)
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
    )
    pack = ui.search("Infosys")
    assert pack.open_intelligence.get("answer_policy") == "aoi_then_kc_kf_then_documents"
    # Backward compatible corpus fields still present
    assert isinstance(pack.knowledge_corpus, dict)
    assert isinstance(pack.knowledge_foundation, dict)


@pytest.mark.asyncio
async def test_aoi_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/aoi/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "AOI"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "kf1" in body["no_redesign"]

        seed = await client.post("/v1/aoi/registry/seed")
        assert seed.status_code == 200
        assert seed.json()["nifty_50"] == 50

        run = await client.post(
            "/v1/aoi/run",
            params={"connector_id": "mospi", "limit_per_connector": 2, "publish": False},
        )
        assert run.status_code == 200
        assert run.json()["totals"]["discovered"] >= 1

        companies = await client.get("/v1/aoi/companies", params={"universe": "nifty_50"})
        assert companies.status_code == 200
        assert companies.json()["count"] == 50

        company = await client.get("/v1/aoi/company/TCS")
        assert company.status_code == 200
        assert company.json()["company"]["nse_symbol"] == "TCS"

        dash = await client.get("/v1/aoi/dashboard")
        assert dash.status_code == 200
        assert "connector_health" in dash.json() or "coverage" in dash.json()

        consult = await client.get("/v1/aoi/consult", params={"q": "Inflation"})
        assert consult.status_code == 200
