"""Immutable market expectation objects."""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.market_expectations_intelligence.provenance import provenance
from knowledge_factory.market_expectations_intelligence.schema import (
    IMEI_VERSION,
    METRICS,
    PHASE_1_SOURCES,
    PHASE_2_SOURCES,
    UNKNOWN,
)


def build_expectation(
    *,
    entity: str,
    metric: str,
    period: str,
    forecast_value: float | int | str,
    available_from: str,
    source: str,
    collector: str,
    kind: str = "guidance",
    forecast_range: dict[str, Any] | None = None,
    consensus: dict[str, Any] | None = None,
    confidence: float = 0.8,
    announcement_date: str | None = None,
    evidence: str | list[str] | None = None,
    notes: str | None = None,
    revision_of: str | None = None,
    revision_sequence: int = 0,
    unit: str | None = None,
    derived_from: list[str] | None = None,
) -> dict[str, Any]:
    ticker = str(entity or "").upper()
    m = str(metric or "").lower()
    if not ticker:
        raise ValueError("entity required")
    if m not in METRICS:
        raise ValueError(f"invalid metric: {metric}")
    if not available_from:
        raise ValueError("available_from required")
    if not source or source == UNKNOWN:
        raise ValueError("source required")
    if source not in PHASE_1_SOURCES and source not in PHASE_2_SOURCES:
        raise ValueError(f"unsupported source: {source}")

    evid = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
    fp = f"{ticker}|{m}|{period}|{forecast_value}|{available_from}|{kind}|{revision_sequence}"
    eid = "EXP-" + hashlib.sha256(fp.encode("utf-8")).hexdigest()[:16].upper()

    # Phase-1 consensus proxy: only from guidance/internal — never invent broker median
    cons = consensus
    if cons is None and kind in ("guidance", "internal_forecast", "consensus_proxy"):
        if isinstance(forecast_value, (int, float)):
            cons = {
                "median": forecast_value,
                "mean": forecast_value,
                "high": (forecast_range or {}).get("high", UNKNOWN),
                "low": (forecast_range or {}).get("low", UNKNOWN),
                "std_dev": UNKNOWN,
                "n_estimates": UNKNOWN,
                "basis": "phase_1_single_source_proxy",
                "licensed_consensus": False,
            }
        else:
            cons = {
                "median": UNKNOWN,
                "mean": UNKNOWN,
                "high": UNKNOWN,
                "low": UNKNOWN,
                "std_dev": UNKNOWN,
                "n_estimates": UNKNOWN,
                "basis": "unavailable",
                "licensed_consensus": False,
            }

    return {
        "expectation_id": eid,
        "entity": ticker,
        "metric": m,
        "period": period,
        "kind": kind,
        "forecast_value": forecast_value,
        "forecast_range": forecast_range or {"low": UNKNOWN, "high": UNKNOWN},
        "unit": unit,
        "consensus": cons,
        "historical_consensus": [],
        "revision_history": [],
        "revision_of": revision_of,
        "revision_sequence": int(revision_sequence),
        "confidence": round(float(confidence), 4),
        "source": source,
        "collector": collector,
        "announcement_date": announcement_date or available_from,
        "available_from": available_from,
        "evidence": evid,
        "validation": {"status": "pending", "gates": []},
        "provenance": provenance(
            source=source,
            collector=collector,
            confidence=confidence,
            derived_from=derived_from or evid[:1],
        ),
        "notes": notes,
        "version": IMEI_VERSION,
        "fabricated": False,
        "immutable": True,
        "licensed_consensus": source == "licensed_consensus_feed",
    }
