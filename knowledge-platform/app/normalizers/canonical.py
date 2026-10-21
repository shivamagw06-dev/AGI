"""Canonical normalizer — every provider becomes AGI language."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.contracts.models import KnowledgeObjectType, RawEvent, Source


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _nested(data: dict[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


class CanonicalNormalizer:
    """Map provider payloads → AGI canonical field dicts + suggested KO type."""

    def normalize(self, event: RawEvent) -> list[dict[str, Any]]:
        if event.source == Source.YAHOO:
            return self._normalize_yahoo(event)
        if event.source == Source.NSE and event.collector_id == "NSEAnnouncementCollector":
            return self._normalize_nse_announcement(event)
        if event.source == Source.NSE and event.collector_id == "NSEBhavcopyCollector":
            return self._normalize_nse_bhavcopy(event)
        if event.source == Source.BSE:
            return self._normalize_bse_action(event)
        if event.source == Source.COMPANY_IR:
            return self._normalize_company_ir(event)
        return []

    def _normalize_yahoo(self, event: RawEvent) -> list[dict[str, Any]]:
        payload = event.payload
        symbol = (event.company_symbol or "").upper()

        # Compact fixture path
        if "marketCap" in payload or "info" in payload:
            info = payload.get("info") if isinstance(payload.get("info"), dict) else payload
            profile = {
                "object_type": KnowledgeObjectType.COMPANY_PROFILE.value,
                "company_symbol": symbol,
                "company_name": info.get("longName") or info.get("shortName") or symbol,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "exchange": info.get("exchange") or "NSE",
                "currency": info.get("currency") or "INR",
                "website": info.get("website"),
                "summary": info.get("longBusinessSummary"),
                # Enrich Company Knowledge with valuation + growth facets
                "pe_ratio": _num(info.get("trailingPE") or info.get("pe_ratio")),
                "pb_ratio": _num(info.get("priceToBook") or info.get("pb_ratio")),
                "market_cap": _num(info.get("marketCap") or info.get("market_cap")),
                "dividend_yield": _num(info.get("dividendYield")),
                "revenue_growth": _num(info.get("revenueGrowth") or info.get("revenue_growth")),
                "earnings_growth": _num(info.get("earningsGrowth") or info.get("earnings_growth")),
                "products": info.get("products") or [],
                "geography": info.get("geography") or [],
                "customers": info.get("customers") or [],
                "management": info.get("management") or [],
            }
            market = {
                "object_type": KnowledgeObjectType.MARKET_SNAPSHOT.value,
                "company_symbol": symbol,
                "as_of": payload.get("as_of") or datetime.now(timezone.utc).isoformat(),
                "last_price": _num(info.get("regularMarketPrice") or info.get("currentPrice") or info.get("last_price")),
                "market_cap": _num(info.get("marketCap") or info.get("market_cap")),
                "pe_ratio": _num(info.get("trailingPE") or info.get("pe_ratio")),
                "pb_ratio": _num(info.get("priceToBook") or info.get("pb_ratio")),
                "dividend_yield": _num(info.get("dividendYield")),
                "volume": _num(info.get("regularMarketVolume") or info.get("volume")),
                "daily_move_pct": _num(info.get("regularMarketChangePercent") or info.get("daily_move_pct")),
                "week_52_low": _num(info.get("fiftyTwoWeekLow") or info.get("week_52_low")),
                "week_52_high": _num(info.get("fiftyTwoWeekHigh") or info.get("week_52_high")),
                "currency": info.get("currency") or "INR",
            }
            out = [profile, market]
            if info.get("revenueGrowth") is not None or info.get("revenue_growth") is not None:
                out.append(
                    {
                        "object_type": KnowledgeObjectType.FINANCIAL_STATEMENT.value,
                        "company_symbol": symbol,
                        "statement_type": "income_growth",
                        "period_end": payload.get("period_end") or datetime.now(timezone.utc).date().isoformat(),
                        "revenue_growth": _num(info.get("revenueGrowth") or info.get("revenue_growth")),
                        "earnings_growth": _num(info.get("earningsGrowth") or info.get("earnings_growth")),
                        "revenue": _num(info.get("totalRevenue") or info.get("revenue")),
                        "ebitda": _num(info.get("ebitda")),
                        "pat": _num(info.get("netIncomeToCommon") or info.get("pat")),
                        "eps": _num(info.get("trailingEps") or info.get("eps")),
                        "cash": _num(info.get("totalCash") or info.get("cash")),
                        "debt": _num(info.get("totalDebt") or info.get("debt")),
                        "pat_margin": _num(info.get("pat_margin") or info.get("profitMargins")),
                        "ebitda_margin": _num(info.get("ebitda_margin") or info.get("ebitdaMargins")),
                    }
                )
            # Optional ownership / analyst facets when present in fixture/live payload
            if any(k in info for k in ("promoters_pct", "fii_pct", "dii_pct", "mutual_funds_pct", "promoter_holding")):
                out.append(
                    {
                        "object_type": KnowledgeObjectType.OWNERSHIP.value,
                        "company_symbol": symbol,
                        "as_of": payload.get("as_of"),
                        "promoters_pct": _num(info.get("promoters_pct") or info.get("promoter_holding")),
                        "fii_pct": _num(info.get("fii_pct") or info.get("foreign_institutions")),
                        "dii_pct": _num(info.get("dii_pct") or info.get("domestic_institutions")),
                        "mutual_funds_pct": _num(info.get("mutual_funds_pct") or info.get("mutual_funds")),
                    }
                )
            if info.get("targetMeanPrice") is not None or info.get("target_price") is not None or info.get("recommendationKey"):
                out.append(
                    {
                        "object_type": KnowledgeObjectType.ANALYST_CONSENSUS.value,
                        "company_symbol": symbol,
                        "as_of": payload.get("as_of"),
                        "target_price": _num(info.get("targetMeanPrice") or info.get("target_price")),
                        "recommendation": info.get("recommendationKey") or info.get("recommendation"),
                        "number_of_analysts": _num(info.get("numberOfAnalystOpinions") or info.get("number_of_analysts")),
                    }
                )
            return out

        chart = payload.get("chart") or {}
        result = _nested(chart, "chart", "result") or []
        meta = result[0].get("meta", {}) if result else {}
        qs = payload.get("quote_summary") or {}
        qs_result = _nested(qs, "quoteSummary", "result") or []
        first = qs_result[0] if qs_result else {}
        asset = first.get("assetProfile") or {}
        summary = first.get("summaryDetail") or {}
        stats = first.get("defaultKeyStatistics") or {}
        price = first.get("price") or {}
        financial = first.get("financialData") or {}

        def raw(node: Any, key: str = "raw") -> Any:
            if isinstance(node, dict):
                return node.get(key, node.get("fmt"))
            return node

        pe = _num(raw(summary.get("trailingPE")) or raw(stats.get("trailingPE")))
        mcap = _num(raw(price.get("marketCap")) or raw(summary.get("marketCap")))
        rev_growth = raw(financial.get("revenueGrowth"))
        profile = {
            "object_type": KnowledgeObjectType.COMPANY_PROFILE.value,
            "company_symbol": symbol,
            "company_name": price.get("longName") or price.get("shortName") or meta.get("shortName") or symbol,
            "sector": asset.get("sector"),
            "industry": asset.get("industry"),
            "exchange": meta.get("exchangeName") or "NSE",
            "currency": meta.get("currency") or price.get("currency") or "INR",
            "website": asset.get("website"),
            "summary": asset.get("longBusinessSummary"),
            "employees": asset.get("fullTimeEmployees"),
            "pe_ratio": pe,
            "pb_ratio": _num(raw(stats.get("priceToBook"))),
            "market_cap": mcap,
            "dividend_yield": _num(raw(summary.get("dividendYield"))),
            "revenue_growth": _num(rev_growth),
            "earnings_growth": _num(raw(financial.get("earningsGrowth"))),
        }
        market = {
            "object_type": KnowledgeObjectType.MARKET_SNAPSHOT.value,
            "company_symbol": symbol,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "last_price": _num(meta.get("regularMarketPrice") or raw(price.get("regularMarketPrice"))),
            "market_cap": mcap,
            "pe_ratio": pe,
            "pb_ratio": _num(raw(stats.get("priceToBook"))),
            "dividend_yield": _num(raw(summary.get("dividendYield"))),
            "volume": _num(meta.get("regularMarketVolume") or raw(price.get("regularMarketVolume"))),
            "week_52_low": _num(raw(summary.get("fiftyTwoWeekLow"))),
            "week_52_high": _num(raw(summary.get("fiftyTwoWeekHigh"))),
            "currency": meta.get("currency") or "INR",
        }
        out = [profile, market]
        if rev_growth is not None:
            out.append(
                {
                    "object_type": KnowledgeObjectType.FINANCIAL_STATEMENT.value,
                    "company_symbol": symbol,
                    "statement_type": "income_growth",
                    "period_end": datetime.now(timezone.utc).date().isoformat(),
                    "revenue_growth": _num(rev_growth),
                    "earnings_growth": _num(raw(financial.get("earningsGrowth"))),
                    "total_revenue": _num(raw(financial.get("totalRevenue"))),
                    "ebitda": _num(raw(financial.get("ebitda"))),
                    "pat": _num(raw(financial.get("netIncomeToCommon"))),
                    "eps": _num(raw(stats.get("trailingEps"))),
                    "cash": _num(raw(financial.get("totalCash"))),
                    "debt": _num(raw(financial.get("totalDebt"))),
                }
            )
        return out

    def _normalize_nse_announcement(self, event: RawEvent) -> list[dict[str, Any]]:
        p = event.payload
        symbol = (event.company_symbol or p.get("symbol") or "").upper()
        return [
            {
                "object_type": KnowledgeObjectType.CORPORATE_EVENT.value,
                "company_symbol": symbol,
                "event_title": p.get("event_title") or p.get("desc") or p.get("subject") or p.get("attchmntText"),
                "event_date": p.get("an_dt") or p.get("sort_date") or p.get("event_date"),
                "event_type": p.get("desc") or p.get("event_type") or "announcement",
                "attachment_url": p.get("attchmntFile") or p.get("attachment_url"),
                "exchange": "NSE",
            }
        ]

    def _normalize_nse_bhavcopy(self, event: RawEvent) -> list[dict[str, Any]]:
        p = event.payload
        row = p.get("row") if isinstance(p.get("row"), dict) else p
        symbol = (event.company_symbol or row.get("symbol") or row.get("SYMBOL") or "").upper()
        return [
            {
                "object_type": KnowledgeObjectType.MARKET_SNAPSHOT.value,
                "company_symbol": symbol,
                "as_of": p.get("trade_date") or datetime.now(timezone.utc).date().isoformat(),
                "last_price": _num(row.get("last_price") or row.get("CLOSE") or row.get("close")),
                "open_price": _num(row.get("OPEN") or row.get("open")),
                "high_price": _num(row.get("HIGH") or row.get("high")),
                "low_price": _num(row.get("LOW") or row.get("low")),
                "volume": _num(row.get("TTL_TRD_QNTY") or row.get("volume")),
                "currency": "INR",
                "exchange": "NSE",
            }
        ]

    def _normalize_bse_action(self, event: RawEvent) -> list[dict[str, Any]]:
        p = event.payload
        symbol = (event.company_symbol or p.get("company_symbol") or p.get("symbol") or "").upper()
        return [
            {
                "object_type": KnowledgeObjectType.CORPORATE_ACTION.value,
                "company_symbol": symbol,
                "action_type": p.get("action_type") or p.get("PURPOSE") or p.get("purpose"),
                "ex_date": p.get("ex_date") or p.get("ExDate") or p.get("exDate"),
                "record_date": p.get("record_date") or p.get("RecordDate"),
                "ratio": p.get("ratio"),
                "amount": _num(p.get("amount") or p.get("dividend")),
                "exchange": "BSE",
            }
        ]

    def _normalize_company_ir(self, event: RawEvent) -> list[dict[str, Any]]:
        p = event.payload
        symbol = (event.company_symbol or p.get("company_symbol") or "").upper()
        return [
            {
                "object_type": KnowledgeObjectType.CORPORATE_EVENT.value,
                "company_symbol": symbol,
                "event_title": p.get("event_title") or "Investor relations update",
                "event_date": p.get("event_date") or datetime.now(timezone.utc).date().isoformat(),
                "event_type": "investor_relations",
                "attachment_url": p.get("ir_url") or event.endpoint,
                "documents": p.get("documents") or [],
                "exchange": None,
            }
        ]
