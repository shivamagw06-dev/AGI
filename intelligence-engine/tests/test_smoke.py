import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.registry import bootstrap_registry
from app.main import app
from app.orchestration.director import ResearchDirector
from app.schemas.models import DeskType, ResearchRunCreate


@pytest.fixture(autouse=True)
def _boot():
    bootstrap_registry()


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "smoke_analyst" in body["agents"]
        assert "cio" in body["agents"]
        assert "macro_economist" in body["agents"]


@pytest.mark.asyncio
async def test_orch_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/orch/status")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["document_id"] == "ORCH"
        assert body["dag_version"] == "orch-1.0.0"


@pytest.mark.asyncio
async def test_smoke_run_requires_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/research/runs", json={"desk": "smoke"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_director_smoke_run():
    director = ResearchDirector()
    run = await director.execute(ResearchRunCreate(desk=DeskType.SMOKE))
    assert run.run_id
    assert run.agent_outputs
    assert run.report is not None
    assert run.report.confidence.score >= 0
    assert run.report.supporting_evidence or run.agent_outputs[0].evidence
