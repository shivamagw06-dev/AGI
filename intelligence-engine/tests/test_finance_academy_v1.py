"""AGI Finance Academy v1 — curriculum understanding tests (not summarisation)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from academy.consumers import for_fle, for_kf, for_ve
from academy.quality import review_corpus
from academy.teaching import run_exam_suite
from app.academy.flags import AcademyFlags
from app.academy.service import AcademyService
from app.academy.store import AcademyStore
from app.main import app


@pytest.fixture
def svc() -> AcademyService:
    return AcademyService(flags=AcademyFlags(academy=True), store=AcademyStore())


def test_academy_health_not_an_engine(svc: AcademyService):
    h = svc.health()
    assert h["status"] == "ok"
    assert h["not_an_engine"] is True
    assert h["not_a_summariser"] is True
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["concept_count"] >= 40
    assert "kf" in h["no_redesign"]


def test_concepts_are_knowledge_objects_not_summaries(svc: AcademyService):
    inflation = svc.get_concept("inflation")
    assert "definition" in inflation
    assert "first_principles" in inflation
    assert inflation["valuation_impact"]
    assert inflation["forecast_impact"]
    assert inflation["industry_impact"]["Banks"]
    assert inflation["company_impact"]["HDFC Bank"]
    assert inflation["sources"]
    blob = " ".join(
        [
            inflation["definition"],
            inflation["purpose"],
            " ".join(inflation["first_principles"]),
        ]
    ).lower()
    assert "chapter summary" not in blob
    assert "this chapter" not in blob


def test_knowledge_graph_and_causal_models(svc: AcademyService):
    graph = svc.graph()
    assert graph["counts"]["concepts"] >= 40
    assert graph["counts"]["edges"] > 0
    causal = svc.causal_models()
    assert causal["count"] >= 5
    repo = next(m for m in causal["models"] if m["model_id"] == "repo_to_construction_earnings")
    assert "Repo Rate ↑" in repo["chain"][0]
    assert "Corporate Earnings" in repo["chain"][-1] or "Construction" in " ".join(repo["chain"])


def test_quality_control_passes(svc: AcademyService):
    qc = svc.quality()
    assert qc["passed"] is True
    assert not qc["duplicates"]
    assert qc["publishable"] >= 40


def test_understanding_exam_suite():
    suite = run_exam_suite()
    assert suite["complete"] is True
    assert suite["passed"] == suite["total"]
    ids = {r["id"] for r in suite["results"]}
    assert {
        "rates_stock_prices",
        "banks_rising_rates",
        "inflation_valuation",
        "gdp_importance",
        "unemployment_lagging",
        "utilities_defensive",
        "growth_discount_sensitivity",
    }.issubset(ids)


def test_soft_consumers_do_not_require_engine_changes(svc: AcademyService):
    kf = svc.consumer("kf", {})
    fle = svc.consumer("fle", {})
    ve = svc.consumer("ve", {})
    assert kf["consumer"] == "KF"
    assert fle["consumer"] == "FLE"
    assert ve["consumer"] == "VE"
    assert for_kf({})["knowledge_objects"]
    assert for_fle({})["drivers"]
    assert for_ve({})["guidance"]


def test_completion_criteria(svc: AcademyService):
    done = svc.completion()
    assert done["complete"] is True
    assert all(done["criteria"].values())


def test_disabled_academy():
    svc = AcademyService(flags=AcademyFlags(academy=False), store=AcademyStore())
    assert svc.health()["status"] == "disabled"
    with pytest.raises(RuntimeError):
        svc.dashboard()


def test_course_covers_mankiw_chapters(svc: AcademyService):
    course = svc.course()
    assert course["chapter_count"] == 36
    assert course["edition"] == "7e"
    assert any(c["chapter"] == 23 for c in course["chapters"])


@pytest.mark.asyncio
async def test_academy_api_routes_and_locked_engines_untouched():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/v1/academy/health")
        assert h.status_code == 200
        body = h.json()
        assert body["not_an_engine"] is True
        assert body["concept_count"] >= 40

        concepts = await client.get("/v1/academy/concepts")
        assert concepts.status_code == 200
        assert concepts.json()["count"] >= 40

        taught = await client.get("/v1/academy/teach/gdp")
        assert taught.status_code == 200
        assert taught.json()["what_it_is"]

        exams = await client.get("/v1/academy/exams")
        assert exams.status_code == 200
        assert exams.json()["suite"]["complete"] is True

        answer = await client.get("/v1/academy/exams/inflation_valuation")
        assert answer.status_code == 200
        assert "discount" in answer.json()["answer"].lower()

        consumer = await client.post("/v1/academy/consumer/iie", json={"concept_id": "monetary_policy"})
        assert consumer.status_code == 200
        assert consumer.json()["consumer"] == "IIE"

        completion = await client.get("/v1/academy/completion")
        assert completion.status_code == 200
        assert completion.json()["complete"] is True

        # Locked engines still expose health (smoke: no import breakage)
        for path in (
            "/v1/kf/health",
            "/v1/iie/health",
            "/v1/fle/health",
            "/v1/ve/health",
            "/v1/fiml/health",
        ):
            r = await client.get(path)
            assert r.status_code == 200, path


def test_review_corpus_helper():
    assert review_corpus()["passed"] is True
