"""Phase 8.2A — Valuation Policy & Applicability Engine contract tests."""

from __future__ import annotations

from valuation_policy import evaluate, health, is_meaningful, model
from valuation_policy.ask import answer_for, is_valuation_policy_question
from valuation_policy.instruments import resolve_instrument
from valuation_policy.production import explanation


def _record(symbol="AAA", **overrides):
    record = {
        "ok": True,
        "symbol": symbol,
        "master": {
            "company_name": "Alpha Industries",
            "sector": "Industrials",
            "industry": "Industrial Machinery",
            "industry_dna": "capital_goods",
        },
        "latest_price": {"close": 100.0, "shares_outstanding": 1_000_000.0},
        "latest_annual": {
            "revenue": 5_000.0,
            "ebitda": 1_000.0,
            "pat": 500.0,
            "equity": 2_000.0,
            "eps": 5.0,
            "debt": 800.0,
            "cash": 300.0,
        },
        "provider_ratios": {"ratios": {"pe": {"company_value": 20.0}}},
        "coverage": {},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(record.get(key), dict):
            record[key] = {**record[key], **value}
        else:
            record[key] = value
    return record


def test_health_contract():
    h = health()
    assert h["ok"] is True
    assert h["version"] == "8.2A"
    assert "unified_valuation_engine" in h["gates"]


def test_bank_primary_is_price_to_book_and_hides_ev():
    policy = evaluate(
        "HDFCBANK",
        record=_record(
            "HDFCBANK",
            master={
                "company_name": "HDFC Bank",
                "sector": "Financials",
                "industry": "Diversified Banks",
                "industry_dna": "banks",
            },
            latest_annual={"eps": 80.0, "pat": 500.0, "equity": 10_000.0, "revenue": 1.0, "ebitda": None},
        ),
    )
    assert policy["ok"] is True
    assert policy["primary_model"] == "PRICE_TO_BOOK"
    assert policy["status"] == "BANKING_MODEL"
    assert "EV_EBITDA" in policy["hidden_models"]
    assert "EV_SALES" in policy["hidden_models"]
    assert policy["confidence"] == "HIGH"
    assert policy["reason"]
    assert is_meaningful("ev_ebitda", policy) is False
    assert is_meaningful("pb", policy) is True
    assert policy["dqiv"]["ok"] is True


def test_loss_making_hides_pe_and_uses_ev_sales():
    policy = evaluate(
        "SWIGGY",
        record=_record(
            "SWIGGY",
            master={
                "company_name": "Swiggy Limited",
                "sector": "Consumer Discretionary",
                "industry": "Internet Platforms",
                "industry_dna": "internet_platforms",
            },
            latest_annual={
                "eps": -12.0,
                "pat": -500.0,
                "revenue": 8_000.0,
                "ebitda": -100.0,
                "equity": 2_000.0,
            },
            provider_ratios={"ratios": {"pe": {"company_value": -21.0}}},
        ),
    )
    assert policy["status"] == "LOSS_MAKING"
    assert policy["primary_model"] == "EV_SALES"
    assert "PE" in policy["hidden_models"]
    assert is_meaningful("pe", policy) is False
    assert "LOSS_MAKING" in policy["reason_codes"]


def test_etf_hides_company_multiples():
    policy = evaluate(
        "BANKBEES",
        record=_record(
            "BANKBEES",
            master={
                "company_name": "BANKBEES",
                "sector": "",
                "industry": "",
                "industry_dna": None,
            },
            latest_annual={},
            provider_ratios={},
        ),
    )
    assert policy["status"] == "ETF"
    assert policy["primary_model"] == "NAV"
    assert "PE" in policy["hidden_models"]
    assert "PRICE_TO_BOOK" in policy["hidden_models"]
    assert "EV_EBITDA" in policy["hidden_models"]


def test_extreme_pe_classified_not_rejected():
    policy = evaluate(
        "NYKAA",
        record=_record(
            "NYKAA",
            master={
                "company_name": "FSN E-Commerce",
                "sector": "Consumer Discretionary",
                "industry": "Internet Platforms",
                "industry_dna": "internet_platforms",
            },
            latest_annual={"eps": 1.0, "pat": 100.0, "revenue": 5_000.0, "ebitda": 200.0, "equity": 1_000.0},
            provider_ratios={"ratios": {"pe": {"company_value": 412.0}}},
        ),
    )
    assert policy["status"] == "EXTREME_VALUATION"
    assert "PE" not in policy["hidden_models"] or policy["primary_model"] == "PE"
    assert any("extreme" in w for w in (policy["dqiv"].get("warnings") or [])) or "EXTREME_VALUATION" in policy["reason_codes"]


def test_capital_goods_baseline_ev_ebitda():
    policy = evaluate("AAA", record=_record())
    assert policy["primary_model"] == "EV_EBITDA"
    assert policy["status"] in {"VALID", "INSUFFICIENT_DATA", "EXTREME_VALUATION"}


def test_every_hidden_metric_has_explanation():
    policy = evaluate(
        "HDFCBANK",
        record=_record(
            "HDFCBANK",
            master={
                "company_name": "HDFC Bank",
                "sector": "Financials",
                "industry_dna": "banks",
                "industry": "Banks",
            },
        ),
    )
    for metric in policy["hidden_metrics"]:
        entry = policy["metrics"][metric]
        assert entry["status"] == "Hidden"
        assert entry["reason"]
        assert entry["confidence"]


def test_model_and_explanation_endpoints():
    record = _record(
        "INFY",
        master={
            "company_name": "Infosys",
            "sector": "Information Technology",
            "industry_dna": "it_services",
            "industry": "IT Consulting",
        },
    )
    m = model("INFY", record=record)
    assert m["primary_model"] == "PE"
    expl = explanation("INFY", record=record)
    assert expl["why"]
    assert expl["ask_summary"]


def test_ask_helpers():
    assert is_valuation_policy_question("How should HDFC Bank be valued?")
    assert is_valuation_policy_question("Why doesn't Swiggy have a P/E?")
    ans = answer_for(
        "SWIGGY",
        "Why doesn't Swiggy have a P/E?",
        record=_record(
            "SWIGGY",
            master={
                "company_name": "Swiggy Limited",
                "industry_dna": "internet_platforms",
                "sector": "Consumer Discretionary",
            },
            latest_annual={"eps": -5.0, "pat": -100.0, "revenue": 3_000.0, "equity": 500.0},
        ),
    )
    assert ans["ok"] is True
    assert "EV/Sales" in ans["answer"] or "EV_SALES" in ans["answer"]
    assert "negative" in ans["answer"].lower() or "Loss" in ans["answer"] or "not meaningful" in ans["answer"].lower()


def test_instrument_resolver():
    etf = resolve_instrument(symbol="BANKBEES", company_name="BANKBEES", sector="")
    assert etf["instrument_type"] == "ETF"
    eq = resolve_instrument(symbol="RELIANCE", company_name="Reliance Industries", sector="Energy")
    assert eq["instrument_type"] == "EQUITY"


def test_uve_gated_by_policy():
    from valuation_engine import service

    out = service.get_company_valuation(
        "HDFCBANK",
        record=_record(
            "HDFCBANK",
            master={
                "company_name": "HDFC Bank",
                "sector": "Financials",
                "industry": "banks",
                "industry_dna": "banks",
            },
            latest_annual={"eps": 80.0, "pat": 500.0, "equity": 10_000.0, "revenue": 1.0, "ebitda": 1.0, "debt": 0, "cash": 0, "book_value": 100},
        ),
    )
    assert out["ok"] is True
    assert out["policy"]["primary_model"] == "PRICE_TO_BOOK"
    assert out["metrics"]["ev_ebitda"]["meaningful"] is False
    assert out["lens"]["primary_metric"] == "pb"
