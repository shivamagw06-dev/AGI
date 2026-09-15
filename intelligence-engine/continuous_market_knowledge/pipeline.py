"""CMKTP pipeline: Collect → Validate → Normalize → Materiality → Learn → Publish."""

from __future__ import annotations

import time
from typing import Any

from continuous_market_knowledge import traces
from continuous_market_knowledge.builders import collect_all, collect_domain_one
from continuous_market_knowledge.learning import generate_learning
from continuous_market_knowledge.materiality import evaluate_materiality
from continuous_market_knowledge.normalization import normalize_draft
from continuous_market_knowledge.publish import publish_mko
from continuous_market_knowledge.schema import CMKTP_VERSION
from continuous_market_knowledge.store import STORE
from continuous_market_knowledge.validation import validate_draft


def run_continuous_ingestion(
    *,
    domains: list[str] | None = None,
    trigger: str | None = None,
) -> dict[str, Any]:
    """Background / event-driven ingestion — never from Ask."""
    t0 = time.perf_counter()
    span = traces.begin(
        "market_collection",
        meta={"domains": domains or "all", "trigger": trigger or "ops_refresh"},
    )

    if domains and len(domains) == 1:
        collected = collect_domain_one(domains[0])
    else:
        collected = collect_all(domains=domains)

    if trigger:
        for d in collected.get("drafts") or []:
            d.trigger = trigger

    STORE.tick_builder(
        "market_intelligence_builder",
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
        vspan = traces.begin("market_validation", meta={"domain": draft.domain_key})
        verdict = validate_draft(draft)
        traces.end(vspan, ok=verdict["ok"], output=verdict)
        if not verdict["ok"]:
            failed += 1
            continue
        validated_n += 1

        nspan = traces.begin("market_normalization", meta={"domain": draft.domain_key})
        mko = normalize_draft(draft)
        traces.end(
            nspan,
            output={
                "mkto_id": mko.mkto_id,
                "version": mko.version,
                "regime": mko.market_regime,
            },
        )

        mspan = traces.begin("market_materiality", meta={"domain": mko.domain_key})
        mat = evaluate_materiality(mko)
        traces.end(mspan, output=mat)
        if mat.get("filtered"):
            ignored += 1

        if mat.get("learn"):
            lspan = traces.begin("market_learning", meta={"domain": mko.domain_key})
            event = generate_learning(mko, materiality=mat)
            if event:
                STORE.add_learning(event)
                mko.learning_generated = True
                learnings.append(event.to_public_dict())
            traces.end(lspan, output={"learning": bool(event), "tier": mat.get("tier")})

        pspan = traces.begin("market_publication", meta={"mkto_id": mko.mkto_id})
        pub = publish_mko(mko)
        traces.end(pspan, output=pub)
        published.append(pub)

    latency = round((time.perf_counter() - t0) * 1000, 2)
    summary = {
        "ok": True,
        "version": CMKTP_VERSION,
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
