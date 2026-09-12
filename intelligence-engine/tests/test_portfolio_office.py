"""Portfolio Office tests — ingestion, recommendations, scenarios, workspace, CIO language."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.registry import bootstrap_registry, list_agents
from app.main import app
from app.orchestration.director import ResearchDirector
from app.portfolio.normalize import build_snapshot, parse_csv_holdings, sector_exposure
from app.portfolio.pack import build_portfolio_package, evaluate_scenario
from app.portfolio.recommend import FORBIDDEN
from app.schemas.models import DeskType, PortfolioIngestRequest, ResearchRunCreate


@pytest.fixture(autouse=True)
def _boot():
    bootstrap_registry()


TOKEN = "dev-intelligence-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_csv_ingestion_and_normalize():
    csv_text = "symbol,weight,sector\nHDFCBANK,40,Banks\nTCS,35,IT\nRELIANCE,25,Energy\n"
    snap = build_snapshot(name="CSV Book", source="csv", csv_text=csv_text)
    assert len(snap.holdings) == 3
    assert abs(sum(h.weight or 0 for h in snap.holdings) - 1.0) < 1e-6
    sectors = sector_exposure(snap)
    assert "Banks" in sectors
    pack = build_portfolio_package(snapshot=snap)
    assert pack.portfolio.portfolio_id
    assert pack.diversification_score is not None
    assert pack.forecast_score is None
    assert pack.risk_score is None
    assert pack.workspace.get("tabs")
    assert "Action Center" in pack.workspace["tabs"]
    assert pack.action_center
    assert pack.monthly_report.get("executive_summary")
    assert pack.timeline


def test_model_and_manual_ingestion():
    model = build_snapshot(source="model", model_id="balanced_india")
    assert len(model.holdings) >= 5
    manual = build_snapshot(
        source="manual",
        holdings=[{"symbol": "INFY", "weight": 0.5, "sector": "IT"}, {"symbol": "SBIN", "weight": 0.5, "sector": "Banks"}],
    )
    assert len(manual.holdings) == 2
    rows = parse_csv_holdings("INFY,0.6\nTCS,0.4\n")
    assert {r.symbol for r in rows} == {"INFY", "TCS"}


def test_recommendation_language_never_trade():
    snap = build_snapshot(
        source="manual",
        holdings=[
            {"symbol": "HDFCBANK", "weight": 0.55, "sector": "Banks"},
            {"symbol": "ICICIBANK", "weight": 0.25, "sector": "Banks"},
            {"symbol": "TCS", "weight": 0.2, "sector": "IT"},
        ],
    )
    pack = build_portfolio_package(snapshot=snap)
    assert pack.recommendations
    blob = " ".join(f"{r.title} {r.reason} {r.verb}" for r in pack.recommendations).lower()
    for word in FORBIDDEN:
        assert word not in blob
    for rec in pack.recommendations:
        assert rec.verb in {"Review", "Research", "Monitor", "Consider", "Investigate"}
        assert rec.evidence
        assert rec.reason


def test_scenario_withholds_invention():
    pack = build_portfolio_package(
        req=PortfolioIngestRequest(source="model", model_id="balanced_india", name="Demo")
    )
    result = evaluate_scenario("What happens if oil rises 20%?", pack)
    assert result["status"] == "withheld"
    assert result["confidence"] is None
    assert result["assumptions"]
    assert "invent" in result["disclaimer"].lower() or "Never invent" in result["disclaimer"]


@pytest.mark.asyncio
async def test_portfolio_desk_agents_registered():
    agents = list_agents()
    for aid in (
        "portfolio_health",
        "portfolio_risk",
        "portfolio_recommendations",
        "portfolio_summary",
    ):
        assert aid in agents


@pytest.mark.asyncio
async def test_director_portfolio_office_run():
    director = ResearchDirector()
    run = await director.execute(
        ResearchRunCreate(
            desk=DeskType.PORTFOLIO,
            query="Portfolio Office test",
            metadata={
                "portfolio": {
                    "name": "Test Book",
                    "source": "manual",
                    "client_id": "c1",
                    "holdings": [
                        {"symbol": "HDFCBANK", "weight": 0.4, "sector": "Banks"},
                        {"symbol": "TCS", "weight": 0.35, "sector": "IT"},
                        {"symbol": "RELIANCE", "weight": 0.25, "sector": "Energy"},
                    ],
                }
            },
        )
    )
    assert run.portfolio is not None
    assert run.report is not None
    assert run.agent_outputs
    assert len(run.agent_outputs) >= 3
    text = (run.report.executive_summary or "").lower()
    # Negation phrases are avoided; assert no trade-imperative wording
    for banned in (" buy ", " sell ", " execute ", "purchase", "liquidate"):
        assert banned not in f" {text} "
    assert "review" in text or "monitor" in text or "portfolio office" in text
    assert run.portfolio.workspace.get("mode") == "portfolio_office"
    assert run.portfolio.action_center


@pytest.mark.asyncio
async def test_api_normalize_and_office():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        norm = await client.post(
            "/v1/portfolio/normalize",
            headers=AUTH,
            json={"source": "model", "model_id": "quality_compounders", "name": "QC"},
        )
        assert norm.status_code == 200, norm.text
        body = norm.json()
        assert body["portfolio"]["holdings"]
        assert "CIO Summary" in body["workspace"]["tabs"]

        scenario = await client.post(
            "/v1/portfolio/scenario",
            headers=AUTH,
            json={"question": "What happens if RBI cuts rates?", "portfolio": {"source": "model", "model_id": "balanced_india"}},
        )
        assert scenario.status_code == 200
        assert scenario.json()["status"] == "withheld"

        office = await client.post(
            "/v1/portfolio/office",
            headers=AUTH,
            json={
                "name": "API Book",
                "source": "manual",
                "holdings": [
                    {"symbol": "INFY", "weight": 0.5, "sector": "IT"},
                    {"symbol": "SBIN", "weight": 0.5, "sector": "Banks"},
                ],
            },
        )
        assert office.status_code == 200, office.text
        run = office.json()
        assert run["portfolio"]
        assert run["report"]
        assert run["desk"] == "portfolio"


def test_memory_retrieval_soft_path_on_portfolio_run_meta():
    # similar_runs soft-fails; package still attaches memory-safe metadata keys
    pack = build_portfolio_package(req=PortfolioIngestRequest(source="model", model_id="balanced_india"))
    assert "Intelligence Core" in pack.components_reused
    assert "Memory (RAG)" in pack.components_reused
    assert "CIO Committee" in pack.components_reused
