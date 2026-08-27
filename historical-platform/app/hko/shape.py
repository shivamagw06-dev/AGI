"""Sprint 8.2 — shape canonical HKO views (institutional, not provider JSON)."""

from __future__ import annotations

from typing import Any

from app.contracts.models import HistoricalObjectType, Source


def shape_historical_price(knowledge: dict[str, Any], *, company: str, date: str, source: Source) -> dict[str, Any]:
    return {
        "object_type": "HistoricalPrice",
        "company": company,
        "date": date,
        "open": knowledge.get("open"),
        "high": knowledge.get("high"),
        "low": knowledge.get("low"),
        "close": knowledge.get("close"),
        "volume": knowledge.get("volume"),
        "market_cap": knowledge.get("market_cap"),
        "adjusted_close": knowledge.get("adjusted_close") or knowledge.get("close"),
        "source": source.value,
    }


def shape_historical_financial(
    knowledge: dict[str, Any], *, company: str, period: str, source: Source
) -> dict[str, Any]:
    revenue = knowledge.get("revenue")
    pat = knowledge.get("net_income") or knowledge.get("pat")
    ebitda = knowledge.get("ebitda")
    margins = knowledge.get("margins") or {}
    if revenue and pat and "pat_margin" not in margins:
        try:
            margins = {**margins, "pat_margin": round(float(pat) / float(revenue), 4)}
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    return {
        "object_type": "HistoricalFinancialStatement",
        "company": company,
        "quarter": period,
        "revenue": revenue,
        "ebitda": ebitda,
        "pat": pat,
        "eps": knowledge.get("eps"),
        "margins": margins,
        "free_cash_flow": knowledge.get("free_cash_flow") or knowledge.get("operating_cf"),
        "pe": knowledge.get("pe"),
        "valuation": knowledge.get("valuation"),
        "source": source.value,
    }


def shape_historical_event(
    knowledge: dict[str, Any], *, company: str, date: str, source: Source
) -> dict[str, Any]:
    return {
        "object_type": "HistoricalCorporateEvent",
        "company": company,
        "date": date,
        "event_type": knowledge.get("event_type") or "announcement",
        "description": knowledge.get("subject") or knowledge.get("title") or knowledge.get("description"),
        "importance": knowledge.get("importance") or "Medium",
        "report_type": knowledge.get("report_type"),
        "source": source.value,
    }


def shape_historical_action(
    knowledge: dict[str, Any], *, company: str, date: str, source: Source
) -> dict[str, Any]:
    action = str(knowledge.get("action_type") or "action").lower()
    return {
        "object_type": "HistoricalCorporateAction",
        "company": company,
        "date": date,
        "dividend": knowledge.get("amount") if "dividend" in action else None,
        "split": knowledge.get("details") if "split" in action else None,
        "bonus": knowledge.get("details") if "bonus" in action else None,
        "rights": knowledge.get("details") if "right" in action else None,
        "buyback": knowledge.get("details") if "buyback" in action else None,
        "action_type": knowledge.get("action_type"),
        "details": knowledge.get("details"),
        "source": source.value,
    }


def shape_hko_view(object_type: HistoricalObjectType | str, row: dict[str, Any]) -> dict[str, Any]:
    """Public HKO projection from a stored typed row."""
    knowledge = row.get("knowledge") or {}
    company = row.get("company_symbol") or knowledge.get("company") or ""
    date = row.get("effective_date") or ""
    prov = row.get("provenance") or {}
    try:
        source = Source(prov.get("source") or "derived")
    except Exception:
        source = Source.DERIVED

    ot = object_type.value if isinstance(object_type, HistoricalObjectType) else str(object_type)
    if ot in {HistoricalObjectType.PRICE_HISTORY.value, HistoricalObjectType.PRICE.value, "HistoricalPrice"}:
        return shape_historical_price(knowledge, company=company, date=date, source=source)
    if ot == HistoricalObjectType.FINANCIAL_STATEMENT.value:
        return shape_historical_financial(knowledge, company=company, period=date, source=source)
    if ot == HistoricalObjectType.CORPORATE_EVENT.value:
        return shape_historical_event(knowledge, company=company, date=date, source=source)
    if ot in {HistoricalObjectType.CORPORATE_ACTION.value, HistoricalObjectType.DIVIDEND_HISTORY.value}:
        payload = {**knowledge}
        if ot == HistoricalObjectType.DIVIDEND_HISTORY.value:
            payload.setdefault("action_type", "dividend")
            payload.setdefault("amount", knowledge.get("amount"))
        return shape_historical_action(payload, company=company, date=date, source=source)
    return {
        "object_type": ot,
        "company": company,
        "date": date,
        "knowledge": knowledge,
        "source": source.value,
    }
