"""Module 8 — Business Quality producers.

ROIC, ROE, margins, cash conversion, capital allocation, moat signals,
reinvestment, pricing power, trend — every year when series exist.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.historical import produce_metric_history
from institutional_reasoning.institutional_evidence.provenance import now_iso

BQ_VERSION = "business-quality-v1.0.0"

_METRICS = (
    "ROIC",
    "ROE",
    "EBITDA_Margin",
    "Operating_Margin",
    "Net_Margin",
    "Cash_Conversion",
    "Revenue_Growth",
    "FCF",
)


def produce_business_quality(entity_id: str) -> dict[str, Any]:
    eid = str(entity_id or "").upper()
    yearly: dict[str, dict[str, float]] = {}
    summaries: dict[str, Any] = {}
    for m in _METRICS:
        prod = produce_metric_history(eid, m)
        summaries[m] = {
            "latest": (prod.get("analytics") or {}).get("latest"),
            "average": prod.get("historical_average"),
            "trend": (prod.get("analytics") or {}).get("trend"),
            "validated": prod.get("validated"),
            "coverage": prod.get("coverage"),
            "quality": (prod.get("quality") or {}).get("score"),
        }
        for period, val in (prod.get("series") or {}).items():
            yearly.setdefault(period, {})[m] = val

    # Soft moat / pricing / reinvestment signals from trends (not claims).
    roic_trend = (summaries.get("ROIC") or {}).get("trend")
    margin_trend = (summaries.get("EBITDA_Margin") or {}).get("trend")
    growth = (summaries.get("Revenue_Growth") or {}).get("latest")
    signals = {
        "moat_signals": {
            "roic_level": (summaries.get("ROIC") or {}).get("latest"),
            "roic_trend": roic_trend,
            "note": "Signal only — not a moat conclusion",
        },
        "pricing_power": {
            "margin_trend": margin_trend,
            "note": "Inferred from margin trend only",
        },
        "reinvestment": {
            "revenue_growth": growth,
            "note": "Growth proxy — not capital allocation audit",
        },
        "capital_allocation": {
            "cash_conversion": (summaries.get("Cash_Conversion") or {}).get("latest"),
            "fcf_margin": (summaries.get("FCF") or {}).get("latest"),
            "note": "Requires full cash-flow audit for conclusion",
        },
    }
    observed = [m for m, s in summaries.items() if s.get("latest") is not None]
    return {
        "entity": eid,
        "as_of": now_iso(),
        "yearly": yearly,
        "summaries": summaries,
        "signals": signals,
        "roic": (summaries.get("ROIC") or {}).get("latest"),
        "margins": (summaries.get("EBITDA_Margin") or {}).get("latest")
        or (summaries.get("Operating_Margin") or {}).get("latest"),
        "revenue_quality": (summaries.get("Revenue_Growth") or {}).get("latest"),
        "competitive_position": (summaries.get("ROIC") or {}).get("latest"),
        "observed_metrics": observed,
        "validated": len(observed) >= 3,
        "business_quality_version": BQ_VERSION,
    }
