"""CSKP pipeline: Collect → Validate → Normalize → Materiality → Learn → Publish."""

from __future__ import annotations

import time
from typing import Any

from continuous_sector_knowledge import traces
from continuous_sector_knowledge.builders import collect_all, collect_sector
from continuous_sector_knowledge.learning import generate_learning
from continuous_sector_knowledge.materiality import evaluate_materiality
from continuous_sector_knowledge.normalization import normalize_draft
from continuous_sector_knowledge.publish import publish_sko
from continuous_sector_knowledge.schema import CSKP_VERSION
from continuous_sector_knowledge.store import STORE
from continuous_sector_knowledge.validation import validate_draft


def run_continuous_ingestion(
    *,
    sectors: list[str] | None = None,
    trigger: str | None = None,
) -> dict[str, Any]:
    """Background / event-driven ingestion — never from Ask."""
    t0 = time.perf_counter()
    span = traces.begin(
        "sector_collection",
        meta={"sectors": sectors or "all", "trigger": trigger or "ops_refresh"},
    )

    if sectors and len(sectors) == 1:
        collected = collect_sector(sectors[0])
    else:
        collected = collect_all(sectors=sectors)

    # Optional force trigger on drafts
    if trigger:
        for d in collected.get("drafts") or []:
            d.trigger = trigger

    STORE.tick_builder(
        "sector_intelligence_builder",
        ok=bool(collected.get("ok")),
        meta={"n": collected.get("n")},
    )
    traces.end(
        span,
        output={"n": collected.get("n"), "ask_triggered": False, "providers_queried": []},
    )

    published: list[dict[str, Any]] = []
    learnings: list[dict[str, Any]] = []
    ignored = 0
    validated_n = 0
    failed = 0

    for draft in collected.get("drafts") or []:
        # Validation folded into collection stage naming; keep explicit
        verdict = validate_draft(draft)
        if not verdict["ok"]:
            failed += 1
            continue
        validated_n += 1

        nspan = traces.begin("sector_normalization", meta={"sector": draft.sector_key})
        sko = normalize_draft(draft)
        traces.end(
            nspan,
            output={"sko_id": sko.sko_id, "version": sko.version, "outlook": sko.current_outlook},
        )

        mat = evaluate_materiality(sko)
        if mat.get("filtered"):
            ignored += 1

        if mat.get("learn"):
            lspan = traces.begin("sector_learning", meta={"sector": sko.sector_key})
            event = generate_learning(sko, materiality=mat)
            if event:
                STORE.add_learning(event)
                sko.learning_generated = True
                learnings.append(event.to_public_dict())
            traces.end(lspan, output={"learning": bool(event), "tier": mat.get("tier")})

        pspan = traces.begin("sector_publication", meta={"sko_id": sko.sko_id})
        pub = publish_sko(sko)
        traces.end(pspan, output=pub)
        published.append(pub)

    # Refresh span for event-driven path
    rspan = traces.begin("sector_refresh", meta={"published": len(published)})
    traces.end(rspan, output={"published": len(published), "learnings": len(learnings)})

    latency = round((time.perf_counter() - t0) * 1000, 2)
    summary = {
        "ok": True,
        "version": CSKP_VERSION,
        "collected": collected.get("n"),
        "validated": validated_n,
        "validation_failures": failed,
        "published": len(published),
        "learnings": len(learnings),
        "immaterial_filtered_from_learning": ignored,
        "latency_ms": latency,
        "ask_triggered": False,
        "research_triggered": False,
        "forecast_triggered": False,
        "user_interaction": False,
        "providers_queried": [],
        "mode": "event_driven_derived",
        "publications": published[:40],
        "learning_events": learnings[:20],
    }
    STORE.record_run(summary)
    return summary
