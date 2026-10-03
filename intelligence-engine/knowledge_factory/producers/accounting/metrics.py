"""Accounting / business-quality derived metrics from primitives."""

from __future__ import annotations

from typing import Any


def _cagr(first: float, last: float, years: int) -> float | None:
    if years <= 0 or first <= 0 or last <= 0:
        return None
    return round((last / first) ** (1.0 / years) - 1.0, 6)


def produce_accounting(entity: str, primitives: dict[str, dict[str, float]] | None) -> dict[str, Any]:
    e = entity.upper()
    if not primitives:
        return {"found": False, "entity": e, "insufficient": True, "reason": "missing_primitives"}
    rev = primitives.get("revenue") or {}
    ni = primitives.get("net_income") or {}
    ocf = primitives.get("ocf") or {}
    debt = primitives.get("total_debt") or {}
    ebitda = primitives.get("ebitda") or {}
    years = sorted(rev.keys())
    rev_cagr = None
    if len(years) >= 2:
        rev_cagr = _cagr(float(rev[years[0]]), float(rev[years[-1]]), len(years) - 1)
    latest = years[-1] if years else None
    leverage = None
    if latest and ebitda.get(latest) and float(ebitda[latest]) > 0:
        leverage = round(float(debt.get(latest) or 0) / float(ebitda[latest]), 4)
    cash_conv = None
    if latest and ni.get(latest) and float(ni[latest]) != 0:
        cash_conv = round(float(ocf.get(latest) or 0) / float(ni[latest]), 4)
    return {
        "found": True,
        "entity": e,
        "revenue_cagr": rev_cagr,
        "leverage": leverage,
        "cash_conversion": cash_conv,
        "provider": "kf_accounting_producer",
        "derived_not_stored": True,
    }


def produce_business_quality(entity: str, valuation: dict[str, Any] | None) -> dict[str, Any]:
    e = entity.upper()
    metrics = (valuation or {}).get("metrics") or {}
    roic = metrics.get("ROIC") or {}
    points = roic.get("points") or {}
    latest = list(points.values())[-1] if points else None
    return {
        "found": latest is not None,
        "entity": e,
        "roic": latest,
        "quality_score": 80.0 if latest and float(latest) >= 15 else 55.0,
        "provider": "kf_bq_producer",
        "insufficient": latest is None,
    }
