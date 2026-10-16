"""Company Memory Knowledge Compiler — unit tests with injected packs."""

from __future__ import annotations

from company_memory.enrich import merge_memory_into_dossier
from company_memory.production import compile, health, package_for_ask_agi
from company_memory.schema import ENGINE_CODE, MEMORY_SECTIONS, SOURCE_INTELLIGENCE_MAP, VERSION


def _injected() -> dict:
    annual = []
    for i, mult in enumerate([0.7, 0.85, 1.0, 1.15, 1.3, 1.45]):
        y = 2020 + i
        annual.append(
            {
                "period_end": f"{y}-03-31",
                "fiscal_year_label": f"FY{y % 100:02d}",
                "income_statement": {
                    "revenue_from_operations": 1e12 * mult,
                    "ebitda": 2.5e11 * mult,
                    "pat": 2e11 * mult,
                    "pat_owners": 2e11 * mult,
                    "eps_basic": 40 * mult,
                },
                "balance_sheet": {"total_equity": 8e11, "total_debt": 5e10, "cash": 1e11},
                "cash_flow": {"operating_cash_flow": 2.2e11, "free_cash_flow": 1.8e11},
            }
        )
    periods = [
        "2023-06-30",
        "2023-09-30",
        "2023-12-31",
        "2024-03-31",
        "2024-06-30",
        "2024-09-30",
        "2024-12-31",
        "2025-03-31",
    ]
    history = []
    for i, (pe, fii) in enumerate(zip(periods, [44, 45, 46, 47, 48, 49, 50, 51])):
        history.append(
            {
                "period_end": pe,
                "promoter": 72.0,
                "fii": float(fii),
                "dii": 12.0,
                "mutual_funds": 10.0 - i * 0.2,
                "insurance": 4.5,
                "promoter_pledge_pct": 0.0,
            }
        )
    return {
        "market": {"ok": True, "ltp": 4000.0, "provider": "injected", "as_of": "2026-07-28"},
        "ownership": {
            "ok": True,
            "promoter": 72.0,
            "fii": 51.0,
            "dii": 12.0,
            "mutual_funds": 8.6,
            "insurance": 4.5,
            "promoter_pledge_pct": 0.0,
            "quarter_history": history,
            "as_of_quarter": "2025-12-30",
            "source": "injected",
        },
        "earnings": {
            "ok": True,
            "coverage_pct": 100,
            "source": "injected",
            "annual_history": list(reversed(annual)),
            "quarter_history": [],
            "ttm": {
                "available": True,
                "income_statement": {
                    "revenue_from_operations": 1.45e12,
                    "ebitda": 3.6e11,
                    "pat": 2.9e11,
                    "pat_owners": 2.9e11,
                    "eps_basic": 58.0,
                },
            },
            "metrics": {
                "yoy_growth": {"revenue_growth_pct": 12.0, "pat_growth_pct": 11.0, "eps_growth_pct": 10.0},
                "qoq_growth": {"revenue_growth_pct": 2.0},
                "latest_annual": {"roe_pct": 25.0, "roce_pct": 28.0, "ebitda_margin_pct": 25.0, "pat_margin_pct": 20.0},
                "latest_quarter": {"ebitda_margin_pct": 25.0, "pat_margin_pct": 20.0},
            },
        },
        "valuation": {
            "ok": True,
            "current": {"pe": 22.0, "pb": 8.0, "ev_ebitda": 14.0, "peg": 1.5},
            "historical": {
                "pe": {
                    "window": "10Y",
                    "median": 20.0,
                    "high": 30.0,
                    "low": 12.0,
                    "current": 22.0,
                    "percentile": 60.0,
                    "observations": 10,
                }
            },
            "relative": {
                "pe": {
                    "current": 22.0,
                    "peer_median": 20.0,
                    "premium_pct": 10.0,
                    "reasons": ["Higher ROE"],
                }
            },
            "peer_universe": {
                "resolved": True,
                "primary_peers": ["INFY", "HCLTECH"],
                "sector": "Information Technology",
                "industry": "IT Services",
                "source": "valuation_peer_registry",
            },
            "stance": "premium versus peers",
            "observations": ["Trading above peer median valuation."],
        },
    }


def test_health_catalog():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["not_an_llm_trainer"] is True
    assert h["modifies_decision_engine"] is False
    assert "shareholding" in SOURCE_INTELLIGENCE_MAP
    assert "financial_history" in MEMORY_SECTIONS
    assert "BSE" in h["external_sources_catalog"]


def test_compile_injected_memory_and_cid_merge():
    mem = compile(
        "TCS",
        injected=_injected(),
        persist=False,
        skip_live=True,
        allow_live_prices=False,
    )
    assert mem["ok"] is True
    assert mem["recommendation_policy"] == "memory_only_no_buy_sell"
    assert (mem.get("financial_history") or {}).get("available") is True
    assert (mem.get("financial_history") or {}).get("revenue", {}).get("cagr_5y") is not None
    assert (mem.get("ownership_history") or {}).get("trends", {}).get("fii", {}).get("direction") == "rising"
    assert (mem.get("valuation_history") or {}).get("historical_bands", {}).get("pe", {}).get("median") == 20.0
    assert (mem.get("event_timeline") or {}).get("n", 0) >= 1
    assert (mem.get("corporate_history") or {}).get("available") is True
    assert (mem.get("sector_history") or {}).get("sector_key") in {"it_services", "unknown"}

    dossier = merge_memory_into_dossier({"ticker": "TCS", "valuation": {}, "ownership": {}}, mem)
    assert dossier["company_memory"]["ok"] is True
    assert "financial_history" in dossier["memory"]
    assert any(e.get("evidence_type") == "company_memory" for e in dossier.get("evidence") or [])


def test_package_for_ask_agi():
    pkg = package_for_ask_agi(
        "TCS",
        injected=_injected(),
        skip_live=True,
        allow_live_prices=False,
    )
    assert pkg["enabled"] is True
    assert pkg["ok"] is True
    assert pkg["memory"]["ownership_history"]["trends"]["fii"]["direction"] == "rising"
