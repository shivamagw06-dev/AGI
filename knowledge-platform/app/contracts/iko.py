"""Institutional Knowledge Object shapes — what AGI actually learns."""

from __future__ import annotations

from typing import Any

from app.contracts.models import KnowledgeObjectType, Source


def _pct(value: Any) -> float | None:
    """Normalize growth ratios to percent points (0.19 → 19.0)."""
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if abs(n) <= 1.5:
        return round(n * 100.0, 4)
    return round(n, 4)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None and v != [] and v != {}}


def shape_institutional_knowledge(
    object_type: KnowledgeObjectType,
    canonical: dict[str, Any],
    *,
    company_name: str | None = None,
) -> dict[str, Any]:
    """Convert canonical AGI fields into institutional knowledge sections."""
    symbol = (canonical.get("company_symbol") or "").upper() or None

    if object_type == KnowledgeObjectType.COMPANY_PROFILE:
        return _shape_company_profile(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.MARKET_SNAPSHOT:
        return _shape_market_snapshot(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.FINANCIAL_STATEMENT:
        return _shape_financial_statement(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.CORPORATE_EVENT:
        return _shape_corporate_event(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.CORPORATE_ACTION:
        return _shape_corporate_action(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.OWNERSHIP:
        return _shape_ownership(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.ANALYST_CONSENSUS:
        return _shape_analyst(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.NEWS_EVENT:
        return _shape_news(canonical, symbol=symbol, company_name=company_name)
    if object_type == KnowledgeObjectType.SECTOR_KNOWLEDGE:
        return _shape_sector(canonical)
    if object_type == KnowledgeObjectType.MARKET_KNOWLEDGE:
        return _shape_market_knowledge(canonical)
    return _clean(dict(canonical))


def _shape_company_profile(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    name = company_name or c.get("company_name") or symbol
    business = _clean(
        {
            "sector": c.get("sector"),
            "industry": c.get("industry"),
            "products": c.get("products") or [],
            "geography": c.get("geography") or [],
            "customers": c.get("customers") or [],
            "management": c.get("management") or [],
        }
    )
    valuation = _clean(
        {
            "pe": _num(c.get("pe_ratio") or c.get("pe")),
            "pb": _num(c.get("pb_ratio") or c.get("pb")),
            "market_cap": _num(c.get("market_cap")),
            "dividend_yield": _num(c.get("dividend_yield")),
        }
    )
    growth = _clean(
        {
            "revenue_growth_pct": _pct(c.get("revenue_growth")),
            "earnings_growth_pct": _pct(c.get("earnings_growth")),
        }
    )
    knowledge = {
        "company": name,
        "company_symbol": symbol,
        "business": business,
        "industry": c.get("industry"),
        "exchange": c.get("exchange"),
        "currency": c.get("currency"),
        "website": c.get("website"),
        "summary": c.get("summary"),
        "employees": c.get("employees"),
    }
    if valuation:
        knowledge["valuation"] = valuation
    if growth:
        knowledge["growth"] = growth
    # Flat compatibility keys used by transitional readers
    knowledge["company_name"] = name
    knowledge["sector"] = c.get("sector")
    return _clean(knowledge)


def _shape_market_snapshot(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    week52 = _clean(
        {
            "low": _num(c.get("week_52_low") or c.get("fifty_two_week_low")),
            "high": _num(c.get("week_52_high") or c.get("fifty_two_week_high")),
        }
    )
    knowledge = {
        "company": company_name or c.get("company_name") or symbol,
        "company_symbol": symbol,
        "as_of": c.get("as_of"),
        "price": _num(c.get("last_price") or c.get("price")),
        "volume": _num(c.get("volume")),
        "market_cap": _num(c.get("market_cap")),
        "daily_move_pct": _num(c.get("daily_move_pct")),
        "open_price": _num(c.get("open_price")),
        "high_price": _num(c.get("high_price")),
        "low_price": _num(c.get("low_price")),
        "pe_ratio": _num(c.get("pe_ratio")),
        "pb_ratio": _num(c.get("pb_ratio")),
        "dividend_yield": _num(c.get("dividend_yield")),
        "currency": c.get("currency") or "INR",
        "exchange": c.get("exchange"),
    }
    if week52:
        knowledge["week_52_range"] = week52
    # Compatibility
    knowledge["last_price"] = knowledge.get("price")
    return _clean(knowledge)


def _shape_financial_statement(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    margins = _clean(
        {
            "ebitda_margin_pct": _pct(c.get("ebitda_margin")),
            "pat_margin_pct": _pct(c.get("pat_margin") or c.get("net_margin")),
            "gross_margin_pct": _pct(c.get("gross_margin")),
        }
    )
    knowledge = {
        "company": company_name or c.get("company_name") or symbol,
        "company_symbol": symbol,
        "statement_type": c.get("statement_type") or "financials",
        "period_end": c.get("period_end"),
        "revenue": _num(c.get("revenue") or c.get("total_revenue")),
        "ebitda": _num(c.get("ebitda")),
        "pat": _num(c.get("pat") or c.get("net_income")),
        "eps": _num(c.get("eps")),
        "cash": _num(c.get("cash") or c.get("total_cash")),
        "debt": _num(c.get("debt") or c.get("total_debt")),
        "revenue_growth_pct": _pct(c.get("revenue_growth")),
        "earnings_growth_pct": _pct(c.get("earnings_growth")),
        # Compatibility
        "revenue_growth": _num(c.get("revenue_growth")),
        "earnings_growth": _num(c.get("earnings_growth")),
        "total_revenue": _num(c.get("total_revenue") or c.get("revenue")),
    }
    if margins:
        knowledge["margins"] = margins
    return _clean(knowledge)


def _shape_corporate_event(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    return _clean(
        {
            "company": company_name or c.get("company_name") or symbol,
            "company_symbol": symbol,
            "event_type": c.get("event_type") or "announcement",
            "event_title": c.get("event_title"),
            "event_date": c.get("event_date"),
            "category": _classify_event(c.get("event_type") or c.get("event_title")),
            "attachment_url": c.get("attachment_url"),
            "documents": c.get("documents") or [],
            "exchange": c.get("exchange"),
        }
    )


def _classify_event(text: Any) -> str:
    t = str(text or "").lower()
    if "earn" in t or "result" in t:
        return "Earnings"
    if "acqui" in t or "merger" in t:
        return "Acquisition"
    if "board" in t:
        return "Board Meeting"
    if "guidance" in t or "outlook" in t:
        return "Guidance"
    if "regulat" in t or "sebi" in t or "filing" in t:
        return "Regulatory filing"
    if "investor" in t:
        return "Investor Relations"
    return "Corporate Event"


def _shape_corporate_action(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    action = str(c.get("action_type") or "Unknown")
    return _clean(
        {
            "company": company_name or c.get("company_name") or symbol,
            "company_symbol": symbol,
            "action_type": _normalize_action(action),
            "ex_date": c.get("ex_date"),
            "record_date": c.get("record_date"),
            "ratio": c.get("ratio"),
            "amount": _num(c.get("amount")),
            "exchange": c.get("exchange"),
        }
    )


def _normalize_action(action: str) -> str:
    a = action.lower()
    for label in ("Dividend", "Split", "Bonus", "Rights", "Buyback"):
        if label.lower() in a:
            return label
    return action


def _shape_ownership(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    return _clean(
        {
            "company": company_name or c.get("company_name") or symbol,
            "company_symbol": symbol,
            "as_of": c.get("as_of"),
            "promoters_pct": _num(c.get("promoters_pct") or c.get("promoter_holding")),
            "fii_pct": _num(c.get("fii_pct") or c.get("foreign_institutions")),
            "dii_pct": _num(c.get("dii_pct") or c.get("domestic_institutions")),
            "mutual_funds_pct": _num(c.get("mutual_funds_pct") or c.get("mutual_funds")),
            "public_pct": _num(c.get("public_pct")),
        }
    )


def _shape_analyst(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    return _clean(
        {
            "company": company_name or c.get("company_name") or symbol,
            "company_symbol": symbol,
            "as_of": c.get("as_of"),
            "target_price": _num(c.get("target_price") or c.get("targetMeanPrice")),
            "recommendation": c.get("recommendation") or c.get("recommendationKey"),
            "estimate_revisions": c.get("estimate_revisions") or {},
            "number_of_analysts": _num(c.get("number_of_analysts") or c.get("numberOfAnalystOpinions")),
        }
    )


def _shape_news(
    c: dict[str, Any], *, symbol: str | None, company_name: str | None
) -> dict[str, Any]:
    return _clean(
        {
            "company": company_name or c.get("company_name") or symbol,
            "company_symbol": symbol,
            "headline": c.get("headline") or c.get("event_title"),
            "event_type": c.get("event_type") or "News",
            "importance": c.get("importance") or "Medium",
            "event_date": c.get("event_date") or c.get("published_at"),
            "url": c.get("url") or c.get("attachment_url"),
        }
    )


def _shape_sector(c: dict[str, Any]) -> dict[str, Any]:
    return _clean(
        {
            "sector": c.get("sector") or c.get("sector_key"),
            "sector_key": c.get("sector_key"),
            "industry_trends": c.get("industry_trends") or [],
            "sector_valuation": c.get("sector_valuation") or {},
            "leaders": c.get("leaders") or [],
            "risks": c.get("risks") or [],
        }
    )


def _shape_market_knowledge(c: dict[str, Any]) -> dict[str, Any]:
    return _clean(
        {
            "market_key": c.get("market_key") or "india_equity",
            "nifty": c.get("nifty") or {},
            "bank_nifty": c.get("bank_nifty") or {},
            "breadth": c.get("breadth") or {},
            "market_regime": c.get("market_regime"),
            "as_of": c.get("as_of"),
        }
    )


def company_knowledge_view(knowledge: dict[str, Any], *, source: Source, version: int) -> dict[str, Any]:
    """Human/IE-facing Company Knowledge projection (never provider JSON)."""
    valuation = knowledge.get("valuation") or {}
    business = knowledge.get("business") or {}
    growth = knowledge.get("growth") or {}
    return {
        "CompanyKnowledge": {
            "Company": knowledge.get("company") or knowledge.get("company_name"),
            "Valuation": _clean({"PE": valuation.get("pe"), "Market Cap": valuation.get("market_cap")}),
            "Business": _clean(
                {
                    "Sector": business.get("sector") or knowledge.get("sector"),
                    "Industry": business.get("industry") or knowledge.get("industry"),
                }
            ),
            "Growth": _clean(
                {
                    "Revenue Growth": (
                        f"{growth['revenue_growth_pct']}%"
                        if growth.get("revenue_growth_pct") is not None
                        else None
                    )
                }
            ),
            "Source": source.value.title() if isinstance(source, Source) else str(source),
            "Version": version,
        }
    }
