"""Investment Office tests — brief, queue, calendar, scenarios, journal, graph, CIO."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.registry import bootstrap_registry, list_agents
from app.investment_office.calendar import build_calendar
from app.investment_office.graph import build_knowledge_graph
from app.investment_office.journal import build_decision_journal
from app.investment_office.pack import build_investment_office_package, evaluate_office_scenario
from app.investment_office.playbooks import list_playbooks
from app.investment_office.queue import FORBIDDEN, build_research_queue
from app.main import app
from app.orchestration.director import ResearchDirector
from app.schemas.models import DeskType, InvestmentOfficeRequest, ResearchRunCreate


@pytest.fixture(autouse=True)
def _boot():
    bootstrap_registry()


TOKEN = "dev-intelligence-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_playbooks_and_queue_language():
    books = list_playbooks()
    assert len(books) >= 7
    assert any(b["id"] == "indian_banking" for b in books)
    queue = build_research_queue(
        symbols=["TCS", "INFY"],
        watchlist=["RELIANCE"],
        prior_runs=[
            {
                "run_id": "r1",
                "symbols": ["INFY"],
                "metadata": {"forecast_changed": True},
                "report": {"confidence": {"score": 40}},
            }
        ],
        portfolio_recs=[
            {
                "priority": "medium",
                "title": "Research Energy concentration",
                "reason": "Oil exposure increased",
                "symbols": ["RELIANCE"],
                "evidence": ["sector_energy"],
                "confidence": 62,
                "supporting_research": ["Portfolio Office"],
            }
        ],
    )
    assert any(i.symbol == "INFY" and i.priority == "high" for i in queue)
    blob = " ".join(f"{i.title} {i.reason}" for i in queue).lower()
    for w in FORBIDDEN:
        assert w not in blob


def test_calendar_withholds_invented_dates():
    cal = build_calendar(symbols=["INFY"])
    assert any(e.category == "earnings" for e in cal)
    assert any(e.category == "rbi" for e in cal)
    withheld = [e for e in cal if e.status == "withheld"]
    assert withheld
    assert all(e.date is None for e in withheld)


def test_journal_graph_and_package():
    req = InvestmentOfficeRequest(
        watchlist=["INFY", "HDFCBANK"],
        symbols=["TCS"],
        portfolio={"name": "Demo", "source": "model", "model_id": "balanced_india"},
        prior_runs=[
            {
                "run_id": "p1",
                "desk": "equity",
                "symbols": ["INFY"],
                "cio_thesis": "Coverage refresh completed",
                "completed_at": "2026-05-01T10:00:00+00:00",
                "report": {"confidence": {"score": 60}, "executive_summary": "May note"},
            }
        ],
    )
    pack = build_investment_office_package(req)
    assert pack.daily_brief.get("executive_summary")
    assert pack.research_queue
    assert pack.calendar
    assert pack.playbooks
    assert pack.decision_journal
    assert pack.research_timeline
    assert pack.knowledge_graph.get("nodes")
    assert pack.knowledge_graph.get("edges")
    assert "Today's Brief" in pack.workspace["tabs"]
    assert "CIO Summary" in pack.workspace["tabs"]
    assert pack.portfolio_office_link.get("status") == "attached"
    assert "Memory (RAG)" in pack.components_reused
    assert pack.daily_brief.get("forecast_changes", {}).get("status") == "withheld"


def test_scenario_center_withholds():
    result = evaluate_office_scenario(
        "What if RBI cuts rates?",
        portfolio_req={"source": "model", "model_id": "balanced_india", "name": "Demo"},
    )
    assert result["status"] == "withheld"
    assert result["assumptions"]
    assert result["confidence"] is None


@pytest.mark.asyncio
async def test_investment_office_agents_registered():
    agents = list_agents()
    for aid in (
        "investment_brief",
        "investment_queue_calendar",
        "investment_knowledge",
        "investment_summary",
    ):
        assert aid in agents


@pytest.mark.asyncio
async def test_director_investment_office_run():
    director = ResearchDirector()
    run = await director.execute(
        ResearchRunCreate(
            desk=DeskType.INVESTMENT_OFFICE,
            query="Investment Office test",
            metadata={
                "watchlist": ["INFY", "RELIANCE"],
                "symbols": ["TCS"],
                "prior_runs": [
                    {
                        "run_id": "x1",
                        "symbols": ["INFY"],
                        "metadata": {"forecast_changed": True},
                        "report": {"confidence": {"score": 35}, "executive_summary": "soft"},
                    }
                ],
                "portfolio": {
                    "name": "IO Book",
                    "source": "manual",
                    "holdings": [
                        {"symbol": "HDFCBANK", "weight": 0.5, "sector": "Banks"},
                        {"symbol": "TCS", "weight": 0.5, "sector": "IT"},
                    ],
                },
            },
        )
    )
    assert run.investment_office is not None
    assert run.report is not None
    assert len(run.agent_outputs) >= 3
    text = f" { (run.report.executive_summary or '').lower() } "
    for banned in (" buy ", " sell ", " execute "):
        assert banned not in text
    assert run.investment_office.workspace.get("mode") == "investment_office"
    assert run.investment_office.daily_brief
    assert run.investment_office.knowledge_graph.get("nodes")


@pytest.mark.asyncio
async def test_api_investment_office_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        playbooks = await client.get("/v1/investment-office/playbooks", headers=AUTH)
        assert playbooks.status_code == 200
        assert playbooks.json()["playbooks"]

        packaged = await client.post(
            "/v1/investment-office/package",
            headers=AUTH,
            json={"watchlist": ["INFY", "SBIN"], "symbols": ["ITC"]},
        )
        assert packaged.status_code == 200, packaged.text
        body = packaged.json()
        assert body["research_queue"]
        assert body["calendar"]
        assert body["decision_journal"] is not None

        scenario = await client.post(
            "/v1/investment-office/scenario",
            headers=AUTH,
            json={"question": "What if inflation rises?"},
        )
        assert scenario.status_code == 200
        assert scenario.json()["status"] == "withheld"

        office = await client.post(
            "/v1/investment-office/run",
            headers=AUTH,
            json={"watchlist": ["INFY"], "query": "API office run"},
        )
        assert office.status_code == 200, office.text
        run = office.json()
        assert run["desk"] == "investment_office"
        assert run["investment_office"]
        assert run["report"]


def test_memory_components_marker():
    pack = build_investment_office_package(
        InvestmentOfficeRequest(watchlist=["INFY"], prior_runs=[{"run_id": "m1", "desk": "cio_morning", "cio_thesis": "Prior brief"}])
    )
    journal = build_decision_journal(prior_runs=[{"run_id": "m1", "desk": "cio_morning", "cio_thesis": "Prior brief"}])
    assert journal
    graph = build_knowledge_graph(symbols=["INFY"], playbooks=list_playbooks()[:2])
    assert graph["nodes"]
    assert "Research Director" in pack.components_reused
    assert "Portfolio Office" in pack.components_reused
