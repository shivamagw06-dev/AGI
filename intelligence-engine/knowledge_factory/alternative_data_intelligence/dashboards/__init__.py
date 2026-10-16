"""Morning Board — Alternative Data Coverage."""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence import store as iadi_store
from knowledge_factory.alternative_data_intelligence.schema import (
    IADI_VERSION,
    PHASE_1_DATASETS,
    PHASE_2_EXTENSIBLE_DATASETS,
)


def _momentum_for_domain(domain: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [r for r in rows if str(r.get("domain") or "") == domain]
    if not matched:
        return {"domain": domain, "status": "missing", "momentum": None, "trend": None}
    # average momentum across domain datasets
    moms = []
    trends = []
    for r in matched:
        t = r.get("trends") or {}
        if t.get("status") == "ok":
            moms.append(float(t.get("momentum") or 0))
            trends.append(t.get("trend"))
    avg = round(sum(moms) / len(moms), 6) if moms else None
    # majority trend
    trend = None
    if trends:
        trend = max(set(trends), key=trends.count)
    return {
        "domain": domain,
        "datasets": len(matched),
        "momentum": avg,
        "trend": trend,
        "status": "ok" if matched else "missing",
    }


def alternative_data_dashboard(*, ensure: bool = True) -> dict[str, Any]:
    if ensure and iadi_store.dataset_count() == 0:
        from knowledge_factory.alternative_data_intelligence.pipeline import (
            run_alternative_data_pipeline,
        )

        run_alternative_data_pipeline()

    rows = iadi_store.list_datasets()
    n = len(rows)
    ready = sum(1 for r in rows if r.get("institutional_ready"))
    validation_failures = sum(1 for r in rows if (r.get("validation") or {}).get("status") == "fail")

    latest_updates = []
    for r in rows:
        latest_updates.append(
            {
                "dataset_id": r.get("dataset_id"),
                "latest_available": r.get("latest_available"),
                "trend": (r.get("trends") or {}).get("trend"),
                "momentum": (r.get("trends") or {}).get("momentum"),
            }
        )

    missing = [d for d in PHASE_1_DATASETS if not iadi_store.get_dataset(d)]

    # freshness: latest observation date across corpus
    freshest = None
    for r in rows:
        la = r.get("latest_available")
        if la and (freshest is None or str(la) > str(freshest)):
            freshest = la

    domains = (
        "payments",
        "energy",
        "manufacturing",
        "transport",
        "consumer",
        "agriculture",
        "banking",
        "trade",
    )
    domain_momentum = {d: _momentum_for_domain(d, rows) for d in domains}

    # economic momentum = average of available domain momenta
    all_m = [v["momentum"] for v in domain_momentum.values() if v.get("momentum") is not None]
    economic_momentum = round(sum(all_m) / len(all_m), 6) if all_m else None

    return {
        "north_star": "institutional_alternative_data_coverage",
        "version": IADI_VERSION,
        "delivery_phase": "phase_1_high_signal",
        "alternative_data_coverage": {
            "datasets": n,
            "phase_1_target": len(PHASE_1_DATASETS),
            "observations": iadi_store.observation_count(),
            "institutional_ready_pct": round(100.0 * ready / n, 2) if n else 0.0,
        },
        "latest_updates": latest_updates,
        "economic_momentum": economic_momentum,
        "consumer_momentum": domain_momentum["consumer"],
        "manufacturing_momentum": domain_momentum["manufacturing"],
        "transport_momentum": domain_momentum["transport"],
        "energy_momentum": domain_momentum["energy"],
        "agriculture_momentum": domain_momentum["agriculture"],
        "banking_momentum": domain_momentum["banking"],
        "payments_momentum": domain_momentum["payments"],
        "missing_datasets": missing,
        "validation_failures": validation_failures,
        "dataset_freshness": {"latest_observation_date": freshest},
        "phase_2_extensible_count": len(PHASE_2_EXTENSIBLE_DATASETS),
        "fabricated": False,
        "prediction": False,
    }
