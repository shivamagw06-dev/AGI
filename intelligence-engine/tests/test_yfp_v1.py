"""YFP V1 — Yahoo Finance Institutional Provider tests (canonical models only)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import get_settings
from app.market_data.client import MarketDataClient
from app.market_data.providers.yahoo import YahooFinanceProvider
from app.market_data.providers.yahoo_mapper import (
    map_fundamentals_from_chart_meta,
    map_fundamentals_from_quote_summary,
    map_ohlcv_from_chart,
    map_quote_from_chart,
    map_search_results,
)
from app.market_data.providers.yahoo_symbols import from_yahoo_symbol, to_yahoo_symbol
from yfp.enrich import merge_yahoo_into_dossier
from yfp.production import is_yfp_enabled, production_dashboard, quality_gates, search
from yfp.schema import YFP_VERSION


def _chart_payload(symbol="HDFCBANK.NS"):
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": symbol,
                        "currency": "INR",
                        "exchangeName": "NSI",
                        "regularMarketPrice": 1650.5,
                        "chartPreviousClose": 1640.0,
                        "regularMarketVolume": 1_200_000,
                    },
                    "timestamp": [1700000000, 1700086400],
                    "indicators": {
                        "quote": [
                            {
                                "open": [1630.0, 1645.0],
                                "high": [1660.0, 1655.0],
                                "low": [1625.0, 1638.0],
                                "close": [1640.0, 1650.5],
                                "volume": [1_000_000, 1_200_000],
                            }
                        ]
                    },
                    "events": {
                        "dividends": {"1700000000": {"amount": 19.5, "date": 1700000000}},
                        "splits": {},
                    },
                }
            ]
        }
    }


def _quote_summary_payload():
    return {
        "quoteSummary": {
            "result": [
                {
                    "price": {
                        "longName": "HDFC Bank Limited",
                        "symbol": "HDFCBANK.NS",
                        "currency": "INR",
                        "exchangeName": "NSE",
                    },
                    "assetProfile": {
                        "sector": "Financial Services",
                        "industry": "Banks—Regional",
                        "longBusinessSummary": "Private sector bank in India.",
                        "fullTimeEmployees": 200000,
                        "website": "https://www.hdfcbank.com",
                        "country": "India",
                        "companyOfficers": [
                            {"name": "Sashidhar Jagdishan", "title": "Chief Executive Officer"},
                            {"name": "Srinivasan Vaidyanathan", "title": "Chief Financial Officer"},
                        ],
                    },
                    "summaryDetail": {
                        "trailingPE": {"raw": 18.5},
                        "forwardPE": {"raw": 16.2},
                        "marketCap": {"raw": 12_000_000_000_000},
                        "dividendYield": {"raw": 0.012},
                        "fiftyTwoWeekHigh": {"raw": 1800.0},
                        "fiftyTwoWeekLow": {"raw": 1400.0},
                    },
                    "defaultKeyStatistics": {
                        "enterpriseValue": {"raw": 13_000_000_000_000},
                        "enterpriseToEbitda": {"raw": 12.1},
                        "beta": {"raw": 0.9},
                        "bookValue": {"raw": 550.0},
                        "priceToBook": {"raw": 3.0},
                        "pegRatio": {"raw": 1.1},
                    },
                    "financialData": {
                        "returnOnEquity": {"raw": 0.17},
                        "returnOnAssets": {"raw": 0.02},
                        "revenueGrowth": {"raw": 0.12},
                        "operatingMargins": {"raw": 0.25},
                        "profitMargins": {"raw": 0.22},
                        "freeCashflow": {"raw": 1_000_000_000},
                        "currentRatio": {"raw": 1.1},
                        "recommendationKey": "buy",
                    },
                    "recommendationTrend": {
                        "trend": [{"strongBuy": 10, "buy": 20, "hold": 5, "sell": 1, "strongSell": 0}]
                    },
                    "earningsHistory": {
                        "history": [
                            {
                                "period": "-1q",
                                "epsActual": {"raw": 22.0},
                                "epsEstimate": {"raw": 21.0},
                                "surprisePercent": {"raw": 0.05},
                                "quarter": {"fmt": "2024-12-31"},
                            }
                        ]
                    },
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_yahoo_provider_maps_quote_and_fundamentals_canonical():
    transport_calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        transport_calls.append(str(request.url))
        if "chart" in str(request.url):
            return httpx.Response(200, json=_chart_payload())
        if "quoteSummary" in str(request.url):
            return httpx.Response(200, json=_quote_summary_payload())
        return httpx.Response(404, json={"error": "missing"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = YahooFinanceProvider(enabled=True, client=client)
        quote = await provider.get_quote("HDFCBANK")
        fund = await provider.get_fundamentals("HDFCBANK")

    assert quote.object_type == "MarketDataQuote"
    assert quote.symbol == "HDFCBANK"
    assert quote.last == 1650.5
    assert quote.provenance.provider_id == "yahoo"
    # Never leak Yahoo nested raw/fmt wrappers in public fields
    assert not hasattr(quote, "regularMarketPrice")

    assert fund.object_type == "FundamentalSnapshot"
    assert fund.symbol == "HDFCBANK"
    assert fund.metrics["roe"] == 0.17
    assert fund.metrics["sector"] == "Financial Services"
    assert fund.metrics["ceo"] == "Sashidhar Jagdishan"
    assert fund.provenance.provider_id == "yahoo"
    assert "quoteSummary" not in json.dumps(fund.model_dump(mode="json"))


def test_symbol_resolution():
    assert to_yahoo_symbol("HDFCBANK") == "HDFCBANK.NS"
    assert to_yahoo_symbol("Infosys") == "INFY.NS"
    assert to_yahoo_symbol("INFY.NS") == "INFY.NS"
    assert from_yahoo_symbol("INFY.NS") == "INFY"
    # US listings must not be forced onto NSE (META.NS 404 storms hang Ask).
    assert to_yahoo_symbol("META") == "META"
    assert to_yahoo_symbol("AAPL") == "AAPL"
    assert to_yahoo_symbol("facebook") == "META"
    assert to_yahoo_symbol("META", exchange="US") == "META"


def test_mapper_search_canonical():
    hits = map_search_results(
        {
            "quotes": [
                {
                    "symbol": "INFY.NS",
                    "shortname": "Infosys Limited",
                    "exchange": "NSI",
                    "quoteType": "EQUITY",
                    "score": 9.0,
                }
            ]
        }
    )
    assert hits[0]["symbol"] == "INFY"
    assert hits[0]["yahoo_symbol"] == "INFY.NS"
    assert "quoteType" not in hits[0]


def test_registered_in_market_data_client():
    client = MarketDataClient.from_settings(get_settings())
    yahoo = client.yahoo_provider()
    assert yahoo is not None
    assert yahoo.provider_id == "yahoo"
    assert yahoo.priority == 40
    assert yahoo.is_configured() is True
    assert {"quote", "ohlcv", "fundamental", "corporate_action"}.issubset(yahoo.capabilities())
    # Priority order: indianapi < finnhub < fmp < yahoo
    ordered = [p.provider_id for p in client.registry.list_providers()]
    assert ordered.index("yahoo") > ordered.index("fmp")


def test_yahoo_does_not_outrank_fmp_for_failover():
    client = MarketDataClient.from_settings(get_settings())
    providers = client.registry.providers_for("fundamental")
    # FMP may be unconfigured (no key); yahoo should still be present when enabled
    ids = [p.provider_id for p in providers]
    assert "yahoo" in ids
    if "fmp" in ids:
        assert ids.index("fmp") < ids.index("yahoo")


def test_cid_soft_merge_fills_empties_only():
    dossier = {
        "ticker": "HDFCBANK",
        "identity": {"company_name": "Official Name", "sector": None},
        "market_data": {"current_price": 1600.0, "beta": None},
        "financial_metrics": {},
        "valuation": {"current": {}},
        "financial_statements": {"versions": []},
        "evidence_timeline": [],
        "announcements": [],
        "business_profile": {},
        "management": {},
        "peer_comparison": {},
    }
    enrich = {
        "enabled": True,
        "symbol": "HDFCBANK",
        "quote": {"last": 1650.5, "volume": 100},
        "fundamentals": {
            "symbol": "HDFCBANK",
            "metrics": {
                "company_name": "Yahoo Name Should Not Overwrite",
                "sector": "Financial Services",
                "roe": 0.17,
                "beta": 0.9,
                "trailing_pe": 18.5,
            },
        },
        "calendar_events": [
            {
                "event_id": "e1",
                "event_type": "earnings",
                "title": "HDFCBANK earnings",
                "event_time": "2024-12-31",
                "details": {},
            }
        ],
        "corporate_actions": [],
    }
    merged = merge_yahoo_into_dossier(dossier, enrich)
    assert merged["identity"]["company_name"] == "Official Name"  # no overwrite
    assert merged["identity"]["sector"] == "Financial Services"  # fill empty
    assert merged["market_data"]["current_price"] == 1600.0  # keep higher-confidence
    assert merged["market_data"]["beta"] == 0.9
    assert merged["financial_metrics"]["roe"] == 0.17
    assert any(e.get("source_id") == "yahoo" for e in merged["evidence_timeline"])


def test_quality_gates_and_dashboard():
    assert is_yfp_enabled() is True
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["yfp_version"] == YFP_VERSION
    dash = production_dashboard()
    assert dash["programme"] == "YFP"
    assert dash["priority"] == 40


def test_local_search_aliases():
    result = search("HDFC Bank")
    assert result["enabled"] is True
    assert any(h.get("symbol") == "HDFCBANK" for h in result["hits"])


def test_chart_mapper_ohlcv():
    series = map_ohlcv_from_chart(
        _chart_payload(),
        symbol="HDFCBANK.NS",
        interval="1d",
        provenance=YahooFinanceProvider().make_provenance(),
    )
    assert series.object_type == "OHLCV"
    assert series.symbol == "HDFCBANK"
    assert len(series.bars) == 2


def test_fundamentals_mapper_no_yahoo_keys_leaked():
    snap = map_fundamentals_from_quote_summary(
        _quote_summary_payload(),
        symbol="HDFCBANK.NS",
        provenance=YahooFinanceProvider().make_provenance(),
    )
    dumped = snap.model_dump(mode="json")
    blob = json.dumps(dumped)
    assert "quoteSummary" not in blob
    assert "raw" not in blob or "roe" in dumped["metrics"]
    assert dumped["metrics"]["rec_buy"] == 20


def test_chart_meta_fundamentals_fallback():
    payload = _chart_payload("INFY.NS")
    payload["chart"]["result"][0]["meta"]["longName"] = "Infosys Limited"
    payload["chart"]["result"][0]["meta"]["fiftyTwoWeekHigh"] = 1800.0
    payload["chart"]["result"][0]["meta"]["fiftyTwoWeekLow"] = 900.0
    snap = map_fundamentals_from_chart_meta(
        payload,
        symbol="INFY.NS",
        provenance=YahooFinanceProvider().make_provenance(),
    )
    assert snap.symbol == "INFY"
    assert snap.metrics["company_name"] == "Infosys Limited"
    assert snap.metrics["fifty_two_week_high"] == 1800.0


@pytest.mark.asyncio
async def test_fundamentals_falls_back_to_chart_on_401():
    async def handler(request: httpx.Request) -> httpx.Response:
        if "quoteSummary" in str(request.url):
            return httpx.Response(401, json={"finance": {"error": {"code": "Unauthorized"}}})
        if "chart" in str(request.url):
            return httpx.Response(200, json=_chart_payload("INFY.NS"))
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = YahooFinanceProvider(enabled=True, client=client)
        fund = await provider.get_fundamentals("INFY")
    assert fund.symbol == "INFY"
    assert fund.metrics.get("last_price") == 1650.5
