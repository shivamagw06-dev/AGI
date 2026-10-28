"""CMKP continuous pipeline: Collect → Validate → Normalize → Materiality → Learn → Publish."""

from __future__ import annotations

import time
from typing import Any

from continuous_macro_knowledge import traces
from continuous_macro_knowledge.collectors import collect_all, collect_source
from continuous_macro_knowledge.learning import generate_learning
from continuous_macro_knowledge.materiality import evaluate_materiality
from continuous_macro_knowledge.normalization import normalize_release
from continuous_macro_knowledge.publish import publish_mko
from continuous_macro_knowledge.schema import CMKP_VERSION
from continuous_macro_knowledge.store import STORE
from continuous_macro_knowledge.validation import validate_release


def run_continuous_ingestion(
    *,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Background ingestion only — must never be invoked from Ask user requests."""
    t0 = time.perf_counter()
    span = traces.begin("macro_collection", meta={"sources": sources or "all"})

    if sources:
        releases = []
        by_source = {}
        for sid in sources:
            out = collect_source(sid)
            by_source[sid] = {"ok": out["ok"], "n": out.get("n") or 0}
            STORE.tick_collector(sid, ok=bool(out.get("ok")), meta={"n": out.get("n")})
            releases.extend(out.get("releases") or [])
        collected = {"ok": True, "by_source": by_source, "releases": releases, "n": len(releases)}
    else:
        collected = collect_all()
        for sid, meta in (collected.get("by_source") or {}).items():
            STORE.tick_collector(sid, ok=bool(meta.get("ok")), meta=meta)

    traces.end(
        span,
        output={"n": collected.get("n"), "by_source": collected.get("by_source"), "ask_triggered": False},
    )

    published: list[dict[str, Any]] = []
    learnings: list[dict[str, Any]] = []
    ignored = 0
    validated_n = 0
    failed_validation = 0

    for raw in collected.get("releases") or []:
        vspan = traces.begin("macro_validation", meta={"indicator": raw.indicator, "source": raw.source})
        verdict = validate_release(raw)
        traces.end(vspan, ok=verdict["ok"], output=verdict)
        if not verdict["ok"]:
            failed_validation += 1
            continue
        validated_n += 1

        nspan = traces.begin("macro_normalization", meta={"indicator": raw.indicator})
        mko = normalize_release(raw)
        traces.end(
            nspan,
            output={"mko_id": mko.mko_id, "version": mko.version, "delta": mko.normalized.get("delta")},
        )

        mspan = traces.begin("macro_materiality", meta={"indicator": mko.indicator})
        mat = evaluate_materiality(mko)
        traces.end(mspan, output=mat)
        if mat.get("filtered"):
            ignored += 1
            # Still publish knowledge for completeness — but no learning
            # Architectural choice: immaterial still updates store (like company facts),
            # learning is filtered. Repo unchanged → Ignore learning only.
            pass

        learning_out = None
        if mat.get("learn"):
            lspan = traces.begin("macro_learning", meta={"indicator": mko.indicator})
            event = generate_learning(mko, materiality=mat)
            if event:
                STORE.add_learning(event)
                mko.learning_generated = True
                learning_out = event.model_dump(mode="json")
                learnings.append(learning_out)
            traces.end(
                lspan,
                output={"learning": bool(learning_out), "tier": mat.get("tier")},
            )

        pspan = traces.begin("macro_publication", meta={"mko_id": mko.mko_id})
        pub = publish_mko(mko)
        traces.end(pspan, output=pub)
        published.append(pub)

    latency = round((time.perf_counter() - t0) * 1000, 2)
    summary = {
        "ok": True,
        "version": CMKP_VERSION,
        "collected": collected.get("n"),
        "validated": validated_n,
        "validation_failures": failed_validation,
        "published": len(published),
        "learnings": len(learnings),
        "immaterial_filtered_from_learning": ignored,
        "by_source": collected.get("by_source"),
        "latency_ms": latency,
        "ask_triggered": False,
        "research_triggered": False,
        "forecast_triggered": False,
        "user_interaction": False,
        "publications": published[:30],
        "learning_events": learnings[:20],
    }
    STORE.record_run(summary)
    return summary
