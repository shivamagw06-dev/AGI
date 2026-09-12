"""HMKIP pipeline: Collect → Validate → Normalize → Publish (immutable) → Timelines."""

from __future__ import annotations

import time
from typing import Any

from historical_market_intelligence import traces
from historical_market_intelligence.collectors import collect_all, collect_markets, collect_source
from historical_market_intelligence.normalization import normalize_observation
from historical_market_intelligence.schema import HMKIP_VERSION
from historical_market_intelligence.store import STORE
from historical_market_intelligence.timeline import build_all_timelines
from historical_market_intelligence.validation import validate_observation


def run_historical_ingestion(
    *,
    sources: list[str] | None = None,
    markets: list[str] | None = None,
) -> dict[str, Any]:
    """Background historical acquisition — never Ask-triggered."""
    t0 = time.perf_counter()
    span = traces.begin(
        "historical_market_collection",
        meta={"sources": sources or "all", "markets": markets or "all"},
    )

    if markets:
        collected = collect_markets(markets)
        by_source = {"markets_filter": {"ok": True, "n": collected.get("n") or 0}}
        collected = {**collected, "by_source": by_source}
        STORE.tick_collector("markets_filter", ok=True, n=int(collected.get("n") or 0))
    elif sources:
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
    sample_traced = 0

    for idx, raw in enumerate(collected.get("observations") or []):
        detail = idx < 8 or idx % 40 == 0

        if detail:
            vspan = traces.begin(
                "historical_market_validation",
                meta={
                    "market": raw.market_key,
                    "indicator": raw.indicator,
                    "period": raw.period,
                },
            )
        verdict = validate_observation(raw)
        if detail:
            traces.end(vspan, ok=verdict["ok"], output=verdict)
            sample_traced += 1
        if not verdict["ok"]:
            failed += 1
            continue

        if detail:
            nspan = traces.begin(
                "historical_market_normalization",
                meta={"market": raw.market_key, "period": raw.period},
            )
        hmkto = normalize_observation(raw)
        if detail:
            traces.end(
                nspan,
                output={
                    "hmkto_id": hmkto.hmkto_id,
                    "version": hmkto.version,
                    "namespace": hmkto.namespace,
                },
            )

        prior_n = STORE.coverage()["total_observations"]
        if detail:
            pspan = traces.begin(
                "historical_market_publication", meta={"hmkto_id": hmkto.hmkto_id}
            )
        stored = STORE.append(hmkto)
        after_n = STORE.coverage()["total_observations"]
        if after_n > prior_n:
            published_new += 1
        else:
            duplicates += 1
        if detail:
            traces.end(
                pspan,
                output={
                    "hmkto_id": stored.hmkto_id,
                    "version": stored.version,
                    "immutable": True,
                    "new": after_n > prior_n,
                    "sample_traced": sample_traced,
                },
            )

    tspan = traces.begin("historical_market_timeline", meta={"phase": "timelines"})
    timelines = build_all_timelines()
    traces.end(tspan, output=timelines)

    summary = {
        "ok": True,
        "version": HMKIP_VERSION,
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
