"""Finance Academy v1.2 — Applied Corporate Finance (Damodaran) curriculum tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from academy.corporate_finance.teaching import run_exam_suite as acf_exams
from academy.catalog import list_concept_ids, list_courses
from app.academy.flags import AcademyFlags
from app.academy.service import AcademyService
from app.academy.store import AcademyStore
from app.main import app


@pytest.fixture
def svc() -> AcademyService:
    return AcademyService(flags=AcademyFlags(academy=True), store=AcademyStore())


def test_three_course_foundation(svc: AcademyService):
    courses = {c["course_id"] for c in svc.courses()["courses"]}
    assert "mankiw_principles_of_economics" in courses
    assert "damodaran_minimalist_accounting" in courses
    assert "damodaran_applied_corporate_finance" in courses
    h = svc.health()
    assert h["version"].startswith("academy-v1.2")
    assert h["course_count"] >= 3
    assert len(list_concept_ids()) >= 100


def test_acf_canonical_objects(svc: AcademyService):
    rows = svc.list_concepts(course_id="acf")
    assert rows["count"] >= 35
    wacc = svc.get_concept("wacc")
    assert wacc["course_id"] == "damodaran_applied_corporate_finance"
    assert wacc["formula"]
    assert wacc["management_decisions"]
    assert wacc["valuation_impact"]["Cost of Capital"]
    alloc = svc.get_concept("capital_allocation")
    assert "course:corporate_finance" in alloc["tags"]
    assert "chapter summary" not in alloc["definition"].lower()


def test_acf_understanding_exams():
    suite = acf_exams()
    assert suite["complete"] is True
    ids = {r["id"] for r in suite["results"]}
    assert {
        "roic_vs_revenue_growth",
        "wacc_industry_differences",
        "leverage_changes_valuation",
        "buybacks_destroy_value",
        "acquisitions_fail",
        "high_growth_not_value",
        "capital_allocation_management_quality",
    }.issubset(ids)


def test_soft_consumers_iie_ve_fle_irp(svc: AcademyService):
    iie = svc.consumer("iie", {"concept_id": "capital_allocation"})
    assert iie["consumer"] == "IIE"
    assert iie["management_quality"]["capital_allocation"]
    ve = svc.consumer("ve", {})
    assert ve["wacc_guidance"]
    assert "Fade ROIC" in ve["terminal_guidance"]
    fle = svc.consumer("fle", {})
    assert any(d["concept_id"] == "incremental_roic" for d in fle["drivers"])
    irp = svc.consumer("irp", {"concept_id": "value_creation"})
    assert irp["value_creation_frame"]
    eve = svc.consumer("eve", {"net_income": 100, "cfo": 80})
    assert "optimal_capital_structure" in {c["concept_id"] for c in eve["concepts"]}


def test_acf_completion(svc: AcademyService):
    done = svc.completion("acf")
    assert done["complete"] is True
    assert done["criteria"]["roic_wacc_first_class"] is True
    assert done["criteria"]["capital_allocation_first_class"] is True


def test_combined_academy_still_complete(svc: AcademyService):
    done = svc.completion()
    assert done["complete"] is True
    assert len(list_courses()) >= 3


@pytest.mark.asyncio
async def test_acf_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        courses = await client.get("/v1/academy/courses")
        assert courses.status_code == 200
        assert courses.json()["count"] >= 3

        concepts = await client.get("/v1/academy/concepts", params={"course_id": "corporate_finance"})
        assert concepts.status_code == 200
        assert concepts.json()["count"] >= 35

        taught = await client.get("/v1/academy/teach/wacc")
        assert taught.status_code == 200
        assert taught.json()["what_it_is"]

        toolkit = await client.get("/v1/academy/corporate-finance")
        assert toolkit.status_code == 200
        assert toolkit.json()["core_spread"] == "roic_wacc_spread"

        exams = await client.get("/v1/academy/exams", params={"course_id": "acf"})
        assert exams.status_code == 200
        assert exams.json()["suite"]["complete"] is True

        answer = await client.get("/v1/academy/exams/roic_vs_revenue_growth")
        assert answer.status_code == 200
        assert "wacc" in answer.json()["answer"].lower()

        for path in ("/v1/ve/health", "/v1/iie/health", "/v1/academy/health"):
            r = await client.get(path)
            assert r.status_code == 200, path
