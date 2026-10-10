"""AWS P0 — AGI Analyst Workspace (aggregation only)."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.aws.flags import AwsFlags
from app.aws.service import AwsService
from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rms.models import ResearchRequestCreate
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.cre.service import CREService
from app.validation.service import ValidationService


def _stack() -> tuple[KipService, RspService, RmsService, AwsService]:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="AGI ICICI",
            content=(
                "ICICIBANK Investment Thesis preferred private bank.\n"
                "Target price Rs 1400.\nBull Case\n- Growth\nBear Case\n- Stress\n"
                "Theme: credit_growth\nSector: banking Financials\n"
            ),
            tickers=["ICICIBANK"],
            themes=["credit_growth"],
            sectors=["Financials"],
            date=date(2026, 1, 15),
            article_id="aws_agi_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    kip.ingest_broker(
        IngestRequest(
            title="Broker ICICI",
            content="ICICIBANK upgrade Buy banking Financials",
            tickers=["ICICIBANK"],
            date=date(2026, 2, 1),
            broker="Kotak",
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    rms.create_request(
        ResearchRequestCreate(
            title="AWS draft ICICI",
            owner="analyst",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            request_brief="Update ICICIBANK",
            engine_snapshot={"l4": {"side": "long"}, "e01": {"regime": "risk_on"}},
        )
    )
    aws = AwsService(
        kip=kip,
        rsp=rsp,
        rms=rms,
        cre=CREService(),
        validation=ValidationService(),
    )
    return kip, rsp, rms, aws


def test_company_workspace_aggregates_kip():
    _, _, _, aws = _stack()
    ws = aws.company("ICICIBANK")
    assert ws.ticker == "ICICIBANK"
    assert ws.meta.workspace == "company"
    assert ws.house_view is not None
    assert ws.agi_articles or ws.dossier
    assert ws.knowledge_graph is not None
    assert "KIP" in ws.meta.sources
    # No new research logic — soft engine slots may be empty without live states
    assert ws.relative_value is None or "symbol_hint" in ws.relative_value


def test_theme_sector_macro_research_workspaces():
    _, _, rms, aws = _stack()
    theme = aws.theme("credit_growth")
    assert theme.theme_id == "credit_growth"
    assert theme.documents or theme.search_hits is not None

    sector = aws.sector("Financials")
    assert sector.sector_id == "Financials"
    assert sector.company_coverage.get("ICICIBANK", 0) >= 1

    macro = aws.macro()
    assert macro.meta.workspace == "macro"

    # pick an rms research id
    rid = rms.store.list_all()[0].research_id
    research = aws.research(rid)
    assert research.current_draft is not None
    assert research.evidence_package is not None or research.reasoning_package is not None


def test_dashboard_search_copilot():
    _, _, _, aws = _stack()
    dash = aws.dashboard()
    assert "company" in dash.workspaces
    assert dash.platform_health.get("kip")

    search = aws.search("ICICIBANK")
    assert search.hits
    kinds = {h.kind for h in search.hits}
    assert "company" in kinds or "research" in kinds or "broker" in kinds

    copilot = aws.copilot(workspace="company", ticker="ICICIBANK", question="What is house view?")
    assert copilot.answer_policy == "context_aware_never_empty"
    assert copilot.kip or copilot.house_view or copilot.rsp
    assert copilot.question


def test_replay_and_cre_flags():
    _, _, _, aws = _stack()
    # Ensure CRE has data
    aws.cre.evaluate("golden_p0_v1")
    cre = aws.cre_workspace()
    assert cre.scorecards or cre.dashboard is not None or cre.composite is not None

    replay = aws.replay("2026-01-15")
    assert replay.as_of == "2026-01-15"
    assert replay.meta.workspace == "replay"

    disabled = AwsService(flags=AwsFlags(aws=False), kip=KipService())
    with pytest.raises(RuntimeError, match="AWS is disabled"):
        disabled.company("ICICIBANK")

    no_copilot = AwsService(flags=AwsFlags(aws_copilot=False), kip=KipService())
    with pytest.raises(RuntimeError, match="AWS_COPILOT"):
        no_copilot.copilot(ticker="X")


def test_no_new_research_logic_surface():
    import app.aws as aws
    import app.engines as engines

    assert hasattr(aws, "AwsService")
    assert not hasattr(engines, "aws")
    # health contract
    _, _, _, svc = _stack()
    h = svc.health()
    assert h["creates_research_logic"] is False
    assert h["public_website"] is False
    assert "trading" in h["out_of_scope"]


@pytest.mark.asyncio
async def test_aws_http_apis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/aws/health")
        assert health.status_code == 200
        assert health.json()["platform"] == "AWS"
        assert health.json()["flags"]["AWS"] is True

        await client.post(
            "/v1/kip/ingest/agi",
            json={
                "title": "AGI ICICI",
                "content": "ICICIBANK thesis Financials credit_growth target Rs 1400",
                "tickers": ["ICICIBANK"],
                "themes": ["credit_growth"],
                "sectors": ["Financials"],
                "date": "2026-01-15",
                "article_id": "http_aws_1",
            },
        )

        company = await client.get("/v1/aws/company/ICICIBANK")
        assert company.status_code == 200, company.text
        assert company.json()["ticker"] == "ICICIBANK"

        theme = await client.get("/v1/aws/theme/credit_growth")
        assert theme.status_code == 200

        sector = await client.get("/v1/aws/sector/Financials")
        assert sector.status_code == 200

        dash = await client.get("/v1/aws/dashboard")
        assert dash.status_code == 200

        search = await client.get("/v1/aws/search", params={"q": "ICICIBANK"})
        assert search.status_code == 200
        assert search.json()["hits"]

        copilot = await client.get(
            "/v1/aws/copilot",
            params={"workspace": "company", "ticker": "ICICIBANK", "q": "House view?"},
        )
        assert copilot.status_code == 200
        assert copilot.json()["answer_policy"] == "context_aware_never_empty"

        replay = await client.get("/v1/aws/replay/2026-01-15")
        assert replay.status_code == 200

        # CRE workspace may be empty until evaluate — still 200
        cre = await client.get("/v1/aws/cre")
        assert cre.status_code == 200
