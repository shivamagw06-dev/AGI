"""Mistake Intelligence Engine (MIE) — classify why AGIB was wrong."""

from __future__ import annotations

from typing import Any

from institutional_memory.schema import MISTAKE_TYPES
from institutional_memory.store.corpus import get_company, get_portfolio

ERROR_CATALOG = {
    "evidence_error": "Important filing / evidence ignored or underweighted",
    "reasoning_error": "Correct data, incorrect inference",
    "probability_error": "Scenario probability mass miscalibrated",
    "timing_error": "Thesis directionally correct but too early/late",
    "macro_error": "Unexpected RBI/Fed/oil/INR macro shock",
    "management_error": "Guidance relied on too heavily",
    "accounting_error": "Quality / accounting concern missed",
    "portfolio_error": "Concentration or correlation underestimated",
}


def classify_mistakes(ticker: str | None = None, *, portfolio_id: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if ticker:
        company = get_company(ticker)
        if company:
            for m in company.get("mistakes") or []:
                rows.append({**m, "scope": "company", "ticker": company["ticker"]})
    if portfolio_id or not ticker:
        port = get_portfolio(portfolio_id or "agib_core_india")
        if port:
            for m in port.get("mistakes") or []:
                rows.append({**m, "scope": "portfolio", "portfolio_id": port["portfolio_id"]})
    # Ensure each mistake has a valid type
    classified = []
    for m in rows:
        et = str(m.get("error_type") or "reasoning_error")
        if et not in MISTAKE_TYPES:
            et = "reasoning_error"
        classified.append(
            {
                **m,
                "error_type": et,
                "error_label": ERROR_CATALOG.get(et, et),
                "classified": True,
                "rule": "Mistakes are classified — not merely logged as 'forecast missed'",
            }
        )
    by_type: dict[str, list[dict[str, Any]]] = {t: [] for t in MISTAKE_TYPES}
    for m in classified:
        by_type.setdefault(m["error_type"], []).append(m)
    return {
        "count": len(classified),
        "mistakes": classified,
        "by_type": {k: v for k, v in by_type.items() if v},
        "catalog": ERROR_CATALOG,
        "types": list(MISTAKE_TYPES),
    }


def mistake_summary(ticker: str | None = None) -> dict[str, Any]:
    pack = classify_mistakes(ticker)
    top = sorted(
        ((k, len(v)) for k, v in (pack.get("by_type") or {}).items()),
        key=lambda kv: -kv[1],
    )
    return {
        "mistake_count": pack["count"],
        "mistakes": pack.get("mistakes") or [],
        "by_type": pack.get("by_type") or {},
        "dominant_error_types": [{"type": k, "count": c, "label": ERROR_CATALOG.get(k)} for k, c in top[:4]],
        "lessons_from_mistakes": [m.get("lesson") for m in pack.get("mistakes") or [] if m.get("lesson")],
        "catalog": ERROR_CATALOG,
    }
