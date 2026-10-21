"""HMIP pipeline: Collect → Validate → Normalize → Publish (immutable) → Timelines."""

from __future__ import annotations

import time
from typing import Any

from historical_macro_intelligence import traces
from historical_macro_intelligence.collectors import collect_all, collect_source
from historical_macro_intelligence.normalization import normalize_observation
from historical_macro_intelligence.schema import HMIP_VERSION
from historical_macro_intelligence.store import STORE
from historical_macro_intelligence.timeline import build_all_timelines
from historical_macro_intelligence.validation import validate_observation


def run_historical_ingestion(*, sources: list[str] | None = None) -> dict[str, Any]:
    """Background historical acquisition — never Ask-triggered."""
    t0 = time.perf_counter()
    span = traces.begin("historical_macro_collection", meta={"sources": sources or "all"})

    if sources:
        observations = []
        by_source: dict[str, Any] = {}
        for sid in sources:
            out = collect_source(sid)
            by_source[sid] = {"ok": out["ok"], "n": out.get("n") or 0}
            STORE.tick_collector(sid, ok=bool(out.get("ok")), n=int(out.get("n") or 0))
            observations.extend(out.get("observations") or [])
        collected = {
            "ok": True,
            "by_source": by_source,
            "observations": observations,
            "n": len(observations),
        }
    else:
        collected = collect_all()
        for sid, meta in (collected.get("by_source") or {}).items():
            STORE.tick_collector(sid, ok=bool(meta.get("ok")), n=int(meta.get("n") or 0))

    traces.end(span, output={"n": collected.get("n"), "ask_triggered": False})

    published_new = 0
    duplicates = 0
    failed = 0

    for raw in collected.get("observations") or []:
        vspan = traces.begin(
            "historical_macro_validation",
            meta={"indicator": raw.indicator, "period": raw.period},
        )
        verdict = validate_observation(raw)
        traces.end(vspan, ok=verdict["ok"], output=verdict)
        if not verdict["ok"]:
            failed += 1
            continue

        nspan = traces.begin(
            "historical_macro_normalization",
            meta={"indicator": raw.indicator, "period": raw.period},
        )
        hmko = normalize_observation(raw)
        traces.end(
            nspan,
            output={
                "hmko_id": hmko.hmko_id,
                "version": hmko.version,
                "namespace": hmko.namespace,
            },
        )

        prior_n = STORE.coverage()["total_observations"]
        pspan = traces.begin("historical_macro_publication", meta={"hmko_id": hmko.hmko_id})
        stored = STORE.append(hmko)
        after_n = STORE.coverage()["total_observations"]
        if after_n > prior_n:
            published_new += 1
        else:
            duplicates += 1
        traces.end(
            pspan,
            output={
                "hmko_id": stored.hmko_id,
                "version": stored.version,
                "immutable": True,
                "new": after_n > prior_n,
            },
        )

    tspan = traces.begin("historical_macro_publication", meta={"phase": "timelines"})
    timelines = build_all_timelines()
    traces.end(tspan, output=timelines)

    summary = {
        "ok": True,
        "version": HMIP_VERSION,
        "collected": collected.get("n"),
        "validation_failures": failed,
        "published_new": published_new,
        "published_total": STORE.coverage()["total_observations"],
        "duplicate_checksums_skipped": duplicates,
        "timelines": timelines.get("n"),
        "by_source": collected.get("by_source"),
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "ask_triggered": False,
        "immutable_store": True,
        "providers_queried": [],
    }
    STORE.record_run(summary)
    return summary
