"""Historical Depth nightly pipeline — KF enrichment only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.historical_depth.collectors import collect_universe
from knowledge_factory.historical_depth.dashboard import historical_depth_dashboard
from knowledge_factory.historical_depth.fixtures.seed_history import seed_universe
from knowledge_factory.historical_depth.objects.company import compile_historical_company
from knowledge_factory.historical_depth.objects.macro import compile_historical_macro
from knowledge_factory.historical_depth.objects.sector import compile_historical_sector
from knowledge_factory.historical_depth.packs import build_historical_pack
from knowledge_factory.historical_depth.producers.derived import produce_derived
from knowledge_factory.historical_depth.validators import validate_series
from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.schema import HD_VERSION

PIPELINE_VERSION = "hd-pipeline-v1.0.0"


def run_historical_pipeline(entities: list[str] | None = None) -> dict[str, Any]:
    """Collect → validate → derive → objects → packs → coverage dashboard."""
    t0 = time.perf_counter()
    entities = entities or seed_universe()
    collection = collect_universe(entities)

    validation_failures: list[dict[str, Any]] = []
    for e in entities:
        for kind in ("financials_annual", "financials_quarterly", "prices"):
            series = hd_store.get_series(kind, e)
            verdict = validate_series(series)
            if not verdict["ok"]:
                validation_failures.append({"entity": e, "kind": kind, **verdict})

    for e in entities:
        produce_derived(e)
        compile_historical_company(e)
        build_historical_pack(e)

    compile_historical_macro()

    # Sector objects from seed map
    try:
        from knowledge_factory.fixtures.seed import sector_map

        smap = sector_map()
    except Exception:
        smap = {e: "unknown" for e in entities}
    sectors: dict[str, list[str]] = {}
    for e in entities:
        sectors.setdefault(smap.get(e, "unknown"), []).append(e)
    for sector, members in sectors.items():
        compile_historical_sector(sector, members)

    dash = historical_depth_dashboard(entities=entities)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "hd_version": HD_VERSION,
        "entities": len(entities),
        "collection": {"entities": collection.get("entities"), "status": collection.get("status")},
        "validation_failures": validation_failures,
        "runtime_seconds": runtime,
        "dashboard": dash,
        "status": "ok" if not validation_failures else "degraded",
    }
    hd_store.put_report("historical_pipeline", report)
    return report
