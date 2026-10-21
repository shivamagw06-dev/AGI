"""FIML v1 — Financial Intelligence Model Library (not an engine)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.fiml.flags import FimlFlags
from app.fiml.service import FimlService
from app.fiml.store import FimlStore
from app.main import app
from models.accounting import AccountingModel
from models.consumers import for_ask_agi, for_iie, for_ve
from models.decision import DecisionModel
from models.industry.model import list_industries
from models.registry import ModelRegistry, get_registry
from models.valuation import ValuationKnowledgeModel


INFY_PAYLOAD = {
    "company_symbol": "INFY",
    "revenue_growth": 0.18,
    "gross_margin": 0.32,
    "gross_margin_delta": 0.012,
    "revenue_driver": "pricing",
    "cash_conversion": 0.95,
    "ebit_margin": 0.22,
    "fcf_margin": 0.15,
    "nwc_days": 25,
    "recurring_revenue_share": 0.72,
    "pricing_power": 0.7,
    "switching_costs": 0.65,
    "customer_concentration": 0.22,
    "market_share": 0.12,
    "roic": 0.22,
    "wacc": 0.11,
    "margin_of_safety": 0.2,
    "data_quality": "B",
    "peers": ["TCS", "WIPRO"],
    "evidence_links": ["ev1"],
}


def test_fiml_health_not_an_engine():
    svc = FimlService(flags=FimlFlags(fiml=True), store=FimlStore())
    h = svc.health()
    assert h["programme"] == "FIML"
    assert h["not_an_engine"] is True
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert "ve" in h["no_redesign"]
    assert "ask_agi" in h["no_redesign"]
    assert "accounting" in h["domains"]
    assert "decision" in h["domains"]
    assert len(h["industry_configs"]) >= 10


def test_shared_interfaces_on_all_models():
    reg = ModelRegistry()
    for meta in reg.list_models():
        model = reg.get(meta["domain"])
        for method in ("analyse", "score", "explain", "compare", "monitor", "timeline", "search", "relationships"):
            assert callable(getattr(model, method))


def test_accounting_pricing_power_narrative():
    result = AccountingModel().analyse(INFY_PAYLOAD)
    assert result.object_type == "AccountingAnalysis"
    assert result.score > 0.5
    assert any("pricing" in s.lower() or "pricing" in n.lower() for s, n in zip(result.strengths or [""], result.outputs["accounting"]["notes"] or [""])) or any(
        "pricing" in n.lower() for n in result.outputs["accounting"]["notes"]
    )
    assert result.explainability.get("why")


def test_industry_configs_and_inheritance():
    industries = list_industries()
    assert "it_services" in industries
    assert "banking" in industries
    assert "insurance" in industries
    reg = get_registry()
    infy = reg.analyse("industry", {"company_symbol": "INFY"})
    assert infy["outputs"]["industry"]["industry_id"] == "it_services"
    bank = reg.analyse("industry", {"company_symbol": "HDFCBANK"})
    assert bank["outputs"]["industry"]["industry_id"] == "banking"


def test_valuation_guidance_advises_not_values():
    guide = ValuationKnowledgeModel().analyse({"company_symbol": "HDFCBANK"})
    assert guide.outputs["valuation_guidance"]["primary_model"] == "relative_pb"
    assert guide.explainability.get("performs_valuation") is False
    insurance = ValuationKnowledgeModel().analyse({"industry_id": "insurance", "company_symbol": "HDFCLIFE"})
    assert insurance.outputs["valuation_guidance"]["primary_model"] == "embedded_value"


def test_economics_transmission_relationships():
    reg = get_registry()
    rel = reg.relationships("economics", {"transmission_chain": "repo_to_capex"})
    assert rel["chains"]
    nodes = [r["from"] for r in rel["relationships"]] + [rel["relationships"][-1]["to"]]
    assert nodes[0] == "repo_rate"
    assert "corporate_earnings" in nodes


def test_decision_consistency_and_refuse():
    good = DecisionModel().analyse(INFY_PAYLOAD)
    assert good.outputs["decision"]["suggested_action"] in {"buy", "wait", "avoid"}
    assert good.outputs["decision"]["explainability"]
    weak = DecisionModel().analyse({**INFY_PAYLOAD, "data_quality": "SYNTHETIC", "margin_of_safety": 0.0})
    assert weak.label == "refuse_insufficient_data"


def test_compare_and_consumer_adapters():
    reg = get_registry()
    cmp = reg.compare(
        "competition",
        {**INFY_PAYLOAD, "market_share": 0.2, "company_symbol": "INFY"},
        {"company_symbol": "WIPRO", "market_share": 0.05, "pricing_power": 0.3, "switching_costs": 0.3},
    )
    assert cmp["preferred"]
    ve = for_ve({"company_symbol": "INFY"})
    assert ve["consumer"] == "VE"
    assert "valuation_guidance" in ve
    iie = for_iie(INFY_PAYLOAD)
    assert "business" in iie and "competition" in iie
    ask = for_ask_agi(INFY_PAYLOAD)
    assert ask["answer_policy"] == "institutional_domain_models"
    assert ask["decision"]


def test_capital_allocation_and_governance_scoring():
    reg = get_registry()
    cap = reg.analyse("capital_allocation", {"company_symbol": "INFY", "roic": 0.25, "wacc": 0.11})
    assert cap["label"] in {"disciplined", "mixed", "value_destructive"}
    gov = reg.analyse("governance", {"company_symbol": "INFY", "related_party_risk": 0.7, "board_independence": 0.3})
    assert gov["red_flags"]


def test_disabled_fiml():
    svc = FimlService(flags=FimlFlags(fiml=False), store=FimlStore())
    assert svc.health()["status"] == "disabled"
    with pytest.raises(RuntimeError, match="FIML is disabled"):
        svc.analyse("accounting", INFY_PAYLOAD)


@pytest.mark.asyncio
async def test_fiml_api_routes_and_locked_engines():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/v1/fiml/health")
        assert h.status_code == 200
        body = h.json()
        assert body["not_an_engine"] is True
        assert body["programme"] == "FIML"
        models = await client.get("/v1/fiml/models")
        assert models.status_code == 200
        assert models.json()["count"] >= 10
        analysed = await client.post("/v1/fiml/analyse/accounting", json=INFY_PAYLOAD)
        assert analysed.status_code == 200
        assert analysed.json()["score"] > 0
        bundle = await client.post("/v1/fiml/bundle", json=INFY_PAYLOAD)
        assert bundle.status_code == 200
        assert "decision" in bundle.json()
        consumer = await client.post("/v1/fiml/consumer/ve", json={"company_symbol": "INFY"})
        assert consumer.status_code == 200
        assert consumer.json()["consumer"] == "VE"
        # Locked engines still healthy — FIML did not redesign them
        assert (await client.get("/v1/ve/health")).json()["programme"] == "VE"
        assert (await client.get("/v1/cae/health")).json()["programme"] == "CAE"
        assert (await client.get("/v1/ib/health")).json()["programme"] == "IB"
