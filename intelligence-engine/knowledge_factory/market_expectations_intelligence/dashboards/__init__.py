"""Morning Board — Market Expectations."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence import store as imei_store
from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION, UNKNOWN


def expectations_dashboard(*, ensure: bool = True) -> dict[str, Any]:
    if ensure and imei_store.expectation_count() == 0:
        from knowledge_factory.market_expectations_intelligence.pipeline import (
            run_market_expectations_pipeline,
        )

        run_market_expectations_pipeline()

    expectations = imei_store.list_expectations()
    revisions = imei_store.list_revisions()
    surprises = imei_store.list_surprises()
    narratives = imei_store.list_narratives()

    unknown = [
        e
        for e in expectations
        if e.get("forecast_value") == UNKNOWN
        or (e.get("validation") or {}).get("status") == "fail"
        and "unknown_expectation" in ((e.get("validation") or {}).get("failures") or [])
    ]
    validation_failures = [
        e
        for e in expectations
        if (e.get("validation") or {}).get("status") == "fail"
        and "unknown_expectation" not in ((e.get("validation") or {}).get("failures") or [])
    ]

    upward = sorted(
        [r for r in revisions if r.get("direction") == "upgrade"],
        key=lambda x: abs(float(x.get("magnitude_pct") or 0)),
        reverse=True,
    )[:10]
    downward = sorted(
        [r for r in revisions if r.get("direction") == "downgrade"],
        key=lambda x: abs(float(x.get("magnitude_pct") or 0)),
        reverse=True,
    )[:10]

    rev_surp = sorted(
        [s for s in surprises if s.get("metric") == "revenue"],
        key=lambda x: float(x.get("surprise_pct") or 0),
        reverse=True,
    )[:10]
    eps_surp = sorted(
        [s for s in surprises if s.get("metric") == "eps"],
        key=lambda x: float(x.get("surprise_pct") or 0),
        reverse=True,
    )[:10]

    confs = [float(e.get("confidence") or 0) for e in expectations if e.get("forecast_value") != UNKNOWN]
    avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.0

    from knowledge_factory.market_expectations_intelligence.narratives.registry import narrative_view

    narr = narrative_view()

    ready_n = sum(1 for e in expectations if (e.get("validation") or {}).get("status") == "pass")
    n = len(expectations) or 1

    return {
        "north_star": "institutional_market_expectations_coverage",
        "version": IMEI_VERSION,
        "delivery_phase": "phase_1_public_auditable",
        "expectation_dashboard": {
            "expectations": len(expectations),
            "ready": ready_n,
            "revisions": len(revisions),
            "surprises": len(surprises),
            "narratives": len(narratives),
            "institutional_ready_pct": round(100.0 * ready_n / n, 2),
        },
        "largest_upward_revisions": upward,
        "largest_downward_revisions": downward,
        "revenue_surprise_leaders": rev_surp,
        "eps_surprise_leaders": eps_surp,
        "narrative_changes": narr.get("narrative_changes"),
        "consensus_confidence": {
            "average": avg_conf,
            "basis": "phase_1_guidance_and_internal_forecasts",
            "licensed_consensus": False,
        },
        "unknown_expectations": len(unknown),
        "validation_failures": len(validation_failures),
        "principle": "Markets price expectations, not reality.",
        "fabricated": False,
        "prediction": False,
    }
