"""Company expectation views and expectation-gap comparisons."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence import store as imei_store
from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION, UNKNOWN


def company_expectations(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    t = str(ticker or "").upper()
    rows = imei_store.list_expectations(entity=t, as_of=as_of)
    surprises = imei_store.list_surprises(entity=t, as_of=as_of)
    revisions = imei_store.list_revisions(entity=t, as_of=as_of)
    narratives = [
        n
        for n in imei_store.list_narratives()
        if t in [str(x).upper() for x in (n.get("affected_companies") or [])]
    ]

    # Soft links (never duplicate prior layers — pointers only)
    industry_id = None
    alt_data = None
    gov = None
    try:
        from knowledge_factory.industry_intelligence import store as iivi_store

        industry_id = iivi_store.get_company_industry(t)
    except Exception:
        pass
    try:
        from knowledge_factory.alternative_data_intelligence.links.connect import (
            company_dataset_view,
        )

        alt_data = company_dataset_view(t)
    except Exception:
        pass
    try:
        from knowledge_factory.government_intelligence import store as igri_store

        gov = [p.get("policy_id") for p in igri_store.list_policies() if t in (p.get("affected_companies") or [])][
            :10
        ]
    except Exception:
        gov = []

    return {
        "ticker": t,
        "expectations": rows,
        "n_expectations": len(rows),
        "revisions": revisions,
        "surprises": surprises,
        "narratives": [{"narrative_id": n.get("narrative_id"), "name": n.get("name")} for n in narratives],
        "links": {
            "industry_id": industry_id,
            "alternative_data": alt_data,
            "government_policy_ids": gov,
        },
        "as_of": as_of,
        "version": IMEI_VERSION,
        "fabricated": False,
        "licensed_consensus_assumed": False,
    }


def expectation_gap(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    """Expectation → Actual → Difference for a company (observed only)."""
    surprises = imei_store.list_surprises(entity=ticker, as_of=as_of)
    gaps = []
    for s in surprises:
        gaps.append(
            {
                "metric": s.get("metric"),
                "period": s.get("period"),
                "expectation": s.get("expected_value"),
                "actual": s.get("actual_value"),
                "difference": s.get("difference"),
                "surprise_pct": s.get("surprise_pct"),
                "beat_miss": s.get("beat_miss"),
                "historical_percentile": s.get("historical_percentile"),
                "persistence": s.get("persistence"),
                "context": {
                    "expectation_source": s.get("expectation_source"),
                    "actual_source": s.get("actual_source"),
                },
            }
        )
    beats = sum(1 for g in gaps if g["beat_miss"] == "beat")
    return {
        "ticker": str(ticker or "").upper(),
        "gaps": gaps,
        "n": len(gaps),
        "beat_count": beats,
        "miss_count": sum(1 for g in gaps if g["beat_miss"] == "miss"),
        "repeated_outperformance": beats >= 2,
        "as_of": as_of,
        "version": IMEI_VERSION,
        "fabricated": False,
        "prediction": False,
        "unknown_external_consensus": UNKNOWN,
    }
