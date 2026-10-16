"""Finance Academy v1.1 — Minimalist Accounting (Damodaran) curriculum tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from academy.accounting.earnings_quality import score_earnings_quality
from academy.accounting.red_flags import list_red_flags, score_red_flags
from academy.accounting.teaching import run_exam_suite as accounting_exams
from academy.catalog import list_courses, list_concept_ids
from app.academy.flags import AcademyFlags
from app.academy.service import AcademyService
from app.academy.store import AcademyStore
from app.main import app


@pytest.fixture
def svc() -> AcademyService:
    return AcademyService(flags=AcademyFlags(academy=True), store=AcademyStore())


def test_multi_course_catalog(svc: AcademyService):
    courses = svc.courses()
    ids = {c["course_id"] for c in courses["courses"]}
    assert "mankiw_principles_of_economics" in ids
    assert "damodaran_minimalist_accounting" in ids
    assert svc.health()["version"].startswith("academy-v1.")
    assert svc.health()["course_count"] >= 2


def test_accounting_concepts_investor_objects(svc: AcademyService):
    rows = svc.list_concepts(course_id="damodaran_minimalist_accounting")
    assert rows["count"] >= 30
    eq = svc.get_concept("earnings_quality")
    assert eq["course_id"] == "damodaran_minimalist_accounting"
    assert eq["business_meaning"]
    assert eq["accounting_meaning"]
    assert eq["valuation_impact"]
    assert eq["forecast_impact"]
    assert eq["red_flags"]
    assert "chapter summary" not in eq["definition"].lower()


def test_earnings_quality_score_methodology():
    high = score_earnings_quality({"net_income": 100, "cfo": 110, "assets": 1000, "revenue_quality": 0.9})
    low = score_earnings_quality(
        {
            "net_income": 100,
            "cfo": 40,
            "assets": 1000,
            "revenue_quality": 0.3,
            "exceptionals_pct_ebit": 0.3,
            "aggressive_accounting": True,
            "restatement": True,
        }
    )
    assert high["score"] > low["score"]
    assert low["label"] == "low"
    assert "margin_of_safety" in low["valuation_guidance"]


def test_red_flag_library():
    lib = list_red_flags()
    assert lib["count"] >= 8
    scored = score_red_flags(
        {
            "revenue_growth": 0.2,
            "cfo_growth": 0.0,
            "receivables_growth": 0.25,
            "sales_growth": 0.05,
            "cash_conversion": 0.5,
            "restatement": True,
        }
    )
    assert scored["tripped_count"] >= 3
    assert scored["clean"] is False


def test_accounting_understanding_exams():
    suite = accounting_exams()
    assert suite["complete"] is True
    ids = {r["id"] for r in suite["results"]}
    assert {
        "profit_vs_cash",
        "ebitda_not_cash",
        "working_capital_matters",
        "aggressive_revenue",
        "goodwill_impairments",
        "cash_conversion_matters",
        "accounting_quality_valuation",
    }.issubset(ids)


def test_soft_consumers_eve_ve_fle(svc: AcademyService):
    eve = svc.consumer("eve", {"net_income": 100, "cfo": 50, "assets": 800})
    assert eve["consumer"] == "EVE"
    assert eve["earnings_quality"]["score"] is not None
    ve = svc.consumer("ve", {"net_income": 100, "cfo": 90})
    assert "FCFF" in ve["preferred_cash_flow"] or "FCF" in ve["preferred_cash_flow"]
    fle = svc.consumer("fle", {})
    assert any(d["concept_id"] == "working_capital" for d in fle["drivers"])


def test_accounting_completion(svc: AcademyService):
    done = svc.completion("damodaran_minimalist_accounting")
    assert done["complete"] is True
    assert done["criteria"]["earnings_quality_methodology"] is True
    assert done["criteria"]["red_flag_library"] is True


def test_combined_completion_still_passes(svc: AcademyService):
    done = svc.completion()
    assert done["complete"] is True
    assert len(list_concept_ids()) >= 70
    assert len(list_courses()) >= 2


@pytest.mark.asyncio
async def test_accounting_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        courses = await client.get("/v1/academy/courses")
        assert courses.status_code == 200
        assert courses.json()["count"] >= 2

        concepts = await client.get("/v1/academy/concepts", params={"course_id": "accounting"})
        assert concepts.status_code == 200
        assert concepts.json()["count"] >= 30

        taught = await client.get("/v1/academy/teach/free_cash_flow")
        assert taught.status_code == 200
        assert taught.json()["what_it_is"]

        eq = await client.post("/v1/academy/earnings-quality", json={"net_income": 100, "cfo": 80, "assets": 1000})
        assert eq.status_code == 200
        assert eq.json()["score"] >= 0

        flags = await client.get("/v1/academy/red-flags")
        assert flags.status_code == 200
        assert flags.json()["count"] >= 8

        exams = await client.get("/v1/academy/exams", params={"course_id": "accounting"})
        assert exams.status_code == 200
        assert exams.json()["suite"]["complete"] is True

        eve = await client.post("/v1/academy/consumer/eve", json={"net_income": 100, "cfo": 40, "assets": 1000})
        assert eve.status_code == 200
        assert eve.json()["consumer"] == "EVE"

        # locked engines still healthy
        for path in ("/v1/eve/health", "/v1/ve/health", "/v1/fiml/health", "/v1/academy/health"):
            r = await client.get(path)
            assert r.status_code == 200, path
