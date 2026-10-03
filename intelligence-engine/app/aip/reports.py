"""AIP dashboard / summary reports."""

from __future__ import annotations

from app.aip.flags import AipFlags
from app.aip.models import AipDashboard, ExperimentResult
from app.aip.roadmap import AIP_VERSION, PROGRAMME, WORKSTREAMS
from app.aip.store import AipStore
from app.aip.registry import DynamicWeightRegistry


def build_dashboard(
    *,
    store: AipStore,
    registry: DynamicWeightRegistry,
    flags: AipFlags,
    latest: ExperimentResult | None = None,
) -> AipDashboard:
    stats = store.stats()
    promo = store.get_promotion()
    return AipDashboard(
        programme=PROGRAMME,
        version=AIP_VERSION,
        architecture_status="v1.0.1 LOCKED",
        l4_shadow=True,
        production_influence=False,
        n_weight_sets=len(registry.list()),
        n_experiments=int(stats["n_experiments"]),
        latest_experiment_id=stats["latest_experiment_id"],
        promotion_ready=bool(promo.ready) if promo else False,
        workstreams=[w["id"] for w in WORKSTREAMS],
        flags=flags.as_dict(),
    )
