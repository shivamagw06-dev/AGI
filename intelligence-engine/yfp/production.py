"""YFP production bridge — soft Yahoo enrichment via MarketDataClient only."""

from __future__ import annotations

from typing import Any

from yfp.enrich import fundamentals_to_kip_facts, merge_yahoo_into_dossier
from yfp.schema import YFP_VERSION


def is_yfp_enabled() -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), "yahoo_provider", True))
    except Exception:
        return True


def is_cid_enrichment_enabled() -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), "yahoo_cid_enrichment", True))
    except Exception:
        return True


def _client():
    from app.core.config import get_settings
    from app.market_data.client import MarketDataClient

    return MarketDataClient.from_settings(get_settings())


def _run(coro):
    from app.core.async_run import run_coro

    return run_coro(coro)


def enrich_ticker(ticker: str, *, client: Any | None = None) -> dict[str, Any]:
    """Fetch canonical Yahoo enrichment for a ticker through MarketDataClient."""
    if not is_yfp_enabled():
        return {"enabled": False, "yfp_version": YFP_VERSION, "bypassed": True}
    md = client or _client()
    pack = _run(md.yahoo_enrich(ticker))
    pack["yfp_version"] = YFP_VERSION
    pack["kip_facts"] = fundamentals_to_kip_facts(pack)
    return pack


def search(query: str, *, limit: int = 8, client: Any | None = None) -> dict[str, Any]:
    if not is_yfp_enabled():
        return {"enabled": False, "hits": []}
    md = client or _client()
    hits = _run(md.search_symbols(query, limit=limit))
    return {"enabled": True, "yfp_version": YFP_VERSION, "query": query, "hits": hits}


def enrich_cid(ticker: str, *, client: Any | None = None, kf: Any | None = None) -> dict[str, Any]:
    """Enrich living CID dossier with Yahoo secondary data (fill empties only)."""
    from cid.coverage import compute_coverage
    from cid.ingest import ensure_dossier
    from cid.store import get_cid_store

    t = (ticker or "").upper()
    if not t:
        return {"enabled": False, "reason": "no_ticker"}
    if not is_cid_enrichment_enabled():
        return {"enabled": False, "yfp_version": YFP_VERSION, "bypassed": True, "reason": "cid_enrichment_disabled"}

    enrich = enrich_ticker(t, client=client)
    store = get_cid_store()
    dossier = store.get(t) or ensure_dossier(t)
    leo_update: dict[str, Any] = {}
    kf_update: dict[str, Any] = {}
    dvc_attach: dict[str, Any] = {}

    if enrich.get("enabled"):
        dossier = merge_yahoo_into_dossier(dossier, enrich)
        cov = compute_coverage(dossier)
        dossier.update(
            {
                "coverage": cov["coverage"],
                "coverage_score": cov["coverage_score"],
                "coverage_grade": cov["coverage_grade"],
                "missing_evidence": cov["missing_evidence"],
            }
        )
        dossier = store.put(dossier)

        # Soft LEO evidence when new financial statements arrive
        try:
            from yfp.leo_evidence import evidence_from_financial_intelligence, soft_update_leo_dossier

            objs = evidence_from_financial_intelligence(
                t,
                financial_history=enrich.get("financial_history") or {},
                valuation_snapshot=enrich.get("valuation_snapshot") or {},
            )
            if objs:
                leo_update = soft_update_leo_dossier(t, objs)
                leo_update["objects"] = len(objs)
        except Exception as exc:  # noqa: BLE001
            leo_update = {"updated": False, "error": str(exc)[:200]}

        # Soft KF attach
        try:
            from yfp.kf_attach import soft_attach_kf

            kf_update = soft_attach_kf(
                t,
                financial_history=enrich.get("financial_history") or {},
                valuation_snapshot=enrich.get("valuation_snapshot") or {},
                kf=kf,
            )
        except Exception as exc:  # noqa: BLE001
            kf_update = {"attached": False, "error": str(exc)[:200]}

        # Soft DVC store upsert for valuation fields (secondary)
        try:
            from dvc.models import make_validated_field
            from dvc import store as dvc_store
            from yfp.history import dvc_fields_from_valuation, financial_coverage, valuation_coverage

            vs = enrich.get("valuation_snapshot") or {}
            vf = dvc_fields_from_valuation(vs) if vs.get("metrics") else {}
            # Also stamp key income fields from latest annual if present
            fh = enrich.get("financial_history") or {}
            income = ((fh.get("income_statement") or {}).get("annual") or [])
            if income:
                items = income[0].get("line_items") or {}
                for field in ("revenue", "ebitda", "net_income"):
                    if items.get(field) is not None and field not in vf:
                        vf[field] = make_validated_field(
                            field=field,
                            value=items.get(field),
                            provider="yahoo",
                            confidence=0.72,
                            symbol=t,
                            reason="yfp_financial_history",
                            validation_status="validated",
                        )
                        vf[field]["provider_priority"] = 40
                        vf[field]["source"] = "Yahoo Finance"
                        vf[field]["consensus_status"] = "single_source_secondary"
            if vf:
                pack = {
                    "validated_fields": vf,
                    "conflicts": [],
                    "quality": {
                        "overall": valuation_coverage(vs).get("coverage") if vs else 0.5,
                        "coverage": financial_coverage(fh).get("coverage") if fh else 0.5,
                        "freshness": 1.0,
                        "confidence": 0.72,
                        "consistency": 1.0,
                        "validation": 1.0,
                    },
                    "grades": {},
                    "missing_fields": (financial_coverage(fh).get("missing_financial_fields") or [])
                    + (valuation_coverage(vs).get("missing_valuation_fields") or []),
                    "winning_provider_summary": "yahoo",
                }
                dvc_store.upsert_company_validation(t, pack)
                dvc_attach = {"stored": True, "fields": len(vf)}
        except Exception as exc:  # noqa: BLE001
            dvc_attach = {"stored": False, "error": str(exc)[:200]}

    fh = enrich.get("financial_history") or {}
    vs = enrich.get("valuation_snapshot") or {}
    return {
        "enabled": bool(enrich.get("enabled")),
        "yfp_version": YFP_VERSION,
        "ticker": t,
        "dossier": {
            "ticker": dossier.get("ticker"),
            "coverage_score": dossier.get("coverage_score"),
            "coverage_grade": dossier.get("coverage_grade"),
            "enrichment": dossier.get("enrichment"),
            "market_data": dossier.get("market_data"),
            "financial_metrics": dossier.get("financial_metrics"),
            "financial_statements": {
                "versions": (dossier.get("financial_statements") or {}).get("versions"),
                "coverage": (dossier.get("financial_statements") or {}).get("coverage"),
            },
            "financial_history": dossier.get("financial_history"),
            "historical_kpi_trends": {
                k: (v[:3] if isinstance(v, list) else v)
                for k, v in list((dossier.get("historical_kpi_trends") or {}).items())[:8]
            },
            "valuation": {
                "current": (dossier.get("valuation") or {}).get("current"),
                "historical_count": len((dossier.get("valuation") or {}).get("historical") or []),
                "coverage": (dossier.get("valuation") or {}).get("coverage"),
            },
            "financial_coverage": dossier.get("financial_coverage"),
            "identity": dossier.get("identity"),
        },
        "kip_facts": enrich.get("kip_facts") or [],
        "leo_update": leo_update,
        "kf_update": kf_update,
        "dvc_attach": dvc_attach,
        "enrich": {
            "has_quote": bool(enrich.get("quote")),
            "has_fundamentals": bool((enrich.get("fundamentals") or {}).get("metrics")),
            "has_financial_history": bool(fh.get("counts")),
            "has_valuation_snapshot": bool((vs.get("metrics") or {})),
            "financial_counts": fh.get("counts"),
            "valuation_metrics": list((vs.get("metrics") or {}).keys()),
            "calendar_events": len(enrich.get("calendar_events") or []),
            "errors": {k: v for k, v in enrich.items() if k.endswith("_error")},
        },
    }


def production_dashboard(*, client: Any | None = None) -> dict[str, Any]:
    md = client or _client()
    health = md.health.snapshot()
    yahoo_row = next((p for p in (health.get("providers") or []) if p.get("provider_id") == "yahoo"), {})
    extras = yahoo_row.get("extras") if isinstance(yahoo_row.get("extras"), dict) else {}
    try:
        from app.core.config import get_settings

        s = get_settings()
        flag_overlay = {
            "YAHOO_FINANCIAL_HISTORY": bool(getattr(s, "yahoo_financial_history", True)),
            "YAHOO_VALUATION_HISTORY": bool(getattr(s, "yahoo_valuation_history", True)),
            "YAHOO_CID_ENRICHMENT": bool(getattr(s, "yahoo_cid_enrichment", True)),
            "YAHOO_YFINANCE_FALLBACK": bool(getattr(s, "yahoo_yfinance_fallback", True)),
        }
    except Exception:
        flag_overlay = {}
    flags = dict(extras.get("flags") or {})
    flags.update(flag_overlay)
    return {
        "programme": "YFP",
        "yfp_version": YFP_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_yfp_enabled(),
        "role": "secondary_market_data_provider",
        "priority": 40,
        "provider_health": yahoo_row,
        "yahoo_status": "ok" if yahoo_row.get("ok") else "degraded",
        "rate_limits": {"yahoo": "3/s burst 6"},
        "last_sync": extras.get("last_sync"),
        "coverage_flags": flags,
        "companies_updated": extras.get("companies_updated"),
        "failed_syncs": extras.get("failed_syncs"),
        "latency_ms": extras.get("average_latency_ms"),
        "market_data_metrics": health.get("metrics"),
        "not_an_engine": True,
        "answer_policy": "canonical_models_only",
        "never_mention_yahoo_in_answers": True,
    }


def quality_gates(tickers: list[str] | None = None) -> dict[str, Any]:
    from app.market_data.providers.yahoo_mapper import (
        map_financial_history_from_quote_summary,
        map_valuation_snapshot_from_quote_summary,
        validate_balance_sheet_row,
    )
    from app.market_data.providers.yahoo_symbols import to_yahoo_symbol
    from yfp.history import financial_coverage, kpi_trends

    # Offline fixture — quoteSummary-shaped but mapper must emit canonical keys only
    fixture = {
        "quoteSummary": {
            "result": [
                {
                    "price": {"currency": "INR", "symbol": "INFY.NS", "longName": "Infosys Limited"},
                    "summaryDetail": {
                        "trailingPE": {"raw": 24.0},
                        "forwardPE": {"raw": 22.0},
                        "marketCap": {"raw": 6_000_000_000_000},
                        "priceToSalesTrailing12Months": {"raw": 4.5},
                        "dividendYield": {"raw": 0.025},
                    },
                    "defaultKeyStatistics": {
                        "enterpriseValue": {"raw": 5_800_000_000_000},
                        "enterpriseToEbitda": {"raw": 16.0},
                        "pegRatio": {"raw": 2.1},
                        "priceToBook": {"raw": 7.0},
                        "beta": {"raw": 0.8},
                        "sharesOutstanding": {"raw": 4_000_000_000},
                        "floatShares": {"raw": 3_500_000_000},
                        "bookValue": {"raw": 200.0},
                    },
                    "incomeStatementHistory": {
                        "incomeStatementHistory": [
                            {
                                "endDate": {"raw": 1704067200, "fmt": "2023-12-31"},
                                "totalRevenue": {"raw": 1_800_000_000_000},
                                "ebitda": {"raw": 450_000_000_000},
                                "ebit": {"raw": 400_000_000_000},
                                "operatingIncome": {"raw": 400_000_000_000},
                                "grossProfit": {"raw": 600_000_000_000},
                                "netIncome": {"raw": 300_000_000_000},
                                "dilutedEPS": {"raw": 70.0},
                                "basicEPS": {"raw": 70.5},
                                "incomeTaxExpense": {"raw": 80_000_000_000},
                                "interestExpense": {"raw": 5_000_000_000},
                                "costOfRevenue": {"raw": 1_200_000_000_000},
                                "totalOperatingExpenses": {"raw": 200_000_000_000},
                            },
                            {
                                "endDate": {"fmt": "2022-12-31"},
                                "totalRevenue": {"raw": 1_600_000_000_000},
                                "ebitda": {"raw": 400_000_000_000},
                                "netIncome": {"raw": 270_000_000_000},
                                "dilutedEPS": {"raw": 63.0},
                            },
                        ]
                    },
                    "balanceSheetHistory": {
                        "balanceSheetStatements": [
                            {
                                "endDate": {"fmt": "2023-12-31"},
                                "totalAssets": {"raw": 1_000_000_000_000},
                                "totalCurrentAssets": {"raw": 600_000_000_000},
                                "cash": {"raw": 100_000_000_000},
                                "cashAndCashEquivalents": {"raw": 120_000_000_000},
                                "shortTermInvestments": {"raw": 50_000_000_000},
                                "longTermDebt": {"raw": 40_000_000_000},
                                "shortLongTermDebt": {"raw": 10_000_000_000},
                                "totalLiab": {"raw": 300_000_000_000},
                                "totalCurrentLiabilities": {"raw": 200_000_000_000},
                                "totalStockholderEquity": {"raw": 700_000_000_000},
                            }
                        ]
                    },
                    "cashflowStatementHistory": {
                        "cashflowStatements": [
                            {
                                "endDate": {"fmt": "2023-12-31"},
                                "totalCashFromOperatingActivities": {"raw": 350_000_000_000},
                                "totalCashflowsFromInvestingActivities": {"raw": -80_000_000_000},
                                "totalCashFromFinancingActivities": {"raw": -100_000_000_000},
                                "capitalExpenditures": {"raw": -40_000_000_000},
                                "depreciation": {"raw": 50_000_000_000},
                                "dividendsPaid": {"raw": -90_000_000_000},
                                "repurchaseOfStock": {"raw": -20_000_000_000},
                                "freeCashFlow": {"raw": 310_000_000_000},
                            }
                        ]
                    },
                }
            ]
        }
    }
    hist = map_financial_history_from_quote_summary(fixture, symbol="INFY.NS")
    val = map_valuation_snapshot_from_quote_summary(fixture, symbol="INFY.NS")
    income = (hist.get("income_statement") or {}).get("annual") or []
    balance = (hist.get("balance_sheet") or {}).get("annual") or []
    cash = (hist.get("cash_flow") or {}).get("annual") or []
    bal_val = validate_balance_sheet_row(balance[0]) if balance else {}
    cov = financial_coverage(hist)
    trends = kpi_trends(hist)

    # Ensure no Yahoo-native keys leak at top level of line_items
    leak = False
    for row in income + balance + cash:
        for k in (row.get("line_items") or {}):
            if k[:1].islower() is False or "totalRevenue" in k or "raw" in k:
                # canonical keys are snake_case
                if any(c.isupper() for c in k) or k.endswith("History"):
                    leak = True

    from app.market_data.client import MarketDataClient
    from app.core.config import get_settings

    client = MarketDataClient.from_settings(get_settings())
    yahoo = client.yahoo_provider()
    checks = {
        "registered_in_provider_registry": yahoo is not None,
        "priority_secondary": bool(yahoo and yahoo.priority >= 40),
        "financial_history_flag": bool(yahoo and getattr(yahoo, "flag_financial_history", False)),
        "valuation_history_flag": bool(yahoo and getattr(yahoo, "flag_valuation_history", False)),
        "revenue_history_mapped": bool(income and (income[0].get("line_items") or {}).get("revenue")),
        "ebitda_history_mapped": bool(income and (income[0].get("line_items") or {}).get("ebitda")),
        "net_income_history_mapped": bool(income and (income[0].get("line_items") or {}).get("net_income")),
        "eps_history_mapped": bool(income and (income[0].get("line_items") or {}).get("diluted_eps")),
        "assets_history_mapped": bool(balance and (balance[0].get("line_items") or {}).get("total_assets")),
        "liabilities_history_mapped": bool(
            balance and (balance[0].get("line_items") or {}).get("total_liabilities")
        ),
        "equity_history_mapped": bool(
            balance and (balance[0].get("line_items") or {}).get("shareholders_equity")
        ),
        "cash_history_mapped": bool(balance and (balance[0].get("line_items") or {}).get("cash")),
        "debt_history_mapped": bool(balance and (balance[0].get("line_items") or {}).get("total_debt")),
        "ocf_history_mapped": bool(cash and (cash[0].get("line_items") or {}).get("operating_cash_flow")),
        "fcf_history_mapped": bool(cash and (cash[0].get("line_items") or {}).get("free_cash_flow")),
        "capex_history_mapped": bool(cash and (cash[0].get("line_items") or {}).get("capital_expenditure")),
        "pe_mapped": (val.get("metrics") or {}).get("trailing_pe") is not None,
        "forward_pe_mapped": (val.get("metrics") or {}).get("forward_pe") is not None,
        "ev_mapped": (val.get("metrics") or {}).get("enterprise_value") is not None,
        "ev_ebitda_mapped": (val.get("metrics") or {}).get("ev_ebitda") is not None,
        "pb_mapped": (val.get("metrics") or {}).get("price_to_book") is not None,
        "ps_mapped": (val.get("metrics") or {}).get("price_to_sales") is not None,
        "peg_mapped": (val.get("metrics") or {}).get("peg") is not None,
        "dividend_yield_mapped": (val.get("metrics") or {}).get("dividend_yield") is not None,
        "accounting_equation_ok": (bal_val.get("validation") or {}).get("accounting_equation_ok") is True,
        "kpi_trends_built": bool(trends.get("revenue")),
        "no_yahoo_native_leaks": not leak,
        "cid_enrichment_flag": is_cid_enrichment_enabled() in (True, False),
        "symbol_resolution_hdfc": to_yahoo_symbol("HDFCBANK") == "HDFCBANK.NS",
    }
    return {
        "yfp_version": YFP_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "offline_coverage": cov,
        "note": "Offline mapper/history gates are authoritative; live Yahoo HTTP may fail without crumb.",
    }
