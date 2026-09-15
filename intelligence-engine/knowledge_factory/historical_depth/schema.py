"""Historical Depth schemas — Knowledge Factory enrichment only.

Reasoning Phases 1–7 remain frozen. Ratios are never stored as primitives;
they are recomputed by historical derived producers.
"""

from __future__ import annotations

from typing import Any

HD_VERSION = "historical-depth-v1.0.0"
HD_SCHEMA_VERSION = "hd-schema-v1.0.0"

# Point-in-time integrity: every record carries availability metadata.
# Queries as of date T may only use records with available_from <= T.

ANNUAL_FIELDS = (
    "price",
    "eps",
    "bvps",
    "revenue",
    "gross_profit",
    "ebitda",
    "ebit",
    "net_income",
    "ocf",
    "fcf",
    "capex",
    "total_debt",
    "cash",
    "shares",
    "equity",
)

QUARTERLY_FIELDS = (
    "revenue",
    "gross_profit",
    "ebit",
    "ebitda",
    "net_income",
    "eps",
    "fcf",
    "cash",
    "total_debt",
    "capex",
    "shares",
)

DERIVED_METRICS = (
    "PE",
    "PB",
    "EV_EBITDA",
    "EV_Sales",
    "ROIC",
    "ROE",
    "ROA",
    "Gross_Margin",
    "Net_Margin",
    "EBIT_Margin",
    "Revenue_Growth",
    "EPS_Growth",
    "Cash_Conversion",
    "Debt_Equity",
    "Net_Debt_EBITDA",
)


def pit_record(
    *,
    entity: str,
    kind: str,
    period: str,
    period_end: str,
    available_from: str,
    payload: dict[str, Any],
    source: str = "fixture",
    confidence: float = 0.9,
) -> dict[str, Any]:
    """Canonical point-in-time record. Never overwrite — append/version."""
    return {
        "hd_schema_version": HD_SCHEMA_VERSION,
        "entity": entity.upper(),
        "kind": kind,
        "period": period,
        "period_end": period_end,
        "available_from": available_from,  # PIT gate — no look-ahead
        "payload": payload,
        "source": source,
        "confidence": confidence,
        "immutable": True,
    }


def timeline_event(
    *,
    entity: str,
    date: str,
    event_type: str,
    title: str,
    source: str,
    evidence: str,
    confidence: float = 0.85,
    available_from: str | None = None,
) -> dict[str, Any]:
    af = available_from or date
    return {
        "hd_schema_version": HD_SCHEMA_VERSION,
        "entity": entity.upper(),
        "kind": "timeline",
        "period": date,
        "period_end": date,
        "date": date,
        "available_from": af,
        "type": event_type,
        "title": title,
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "payload": {"title": title, "type": event_type, "evidence": evidence},
    }


def regime_record(
    *,
    regime_id: str,
    name: str,
    start: str,
    end: str,
    macro_state: dict[str, Any],
    affected_sectors: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "hd_schema_version": HD_SCHEMA_VERSION,
        "regime_id": regime_id,
        "name": name,
        "start": start,
        "end": end,
        "macro_state": macro_state,
        "affected_sectors": affected_sectors or [],
        "tags": tags or [],
    }
