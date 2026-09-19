"""Stage 2 — Evidence importance ordering + framework input binding."""

from __future__ import annotations

from typing import Any

from ask_pipeline.answer_assembly.schema import DOMAIN_PRIORITY


def order_evidence(
    classified: dict[str, Any],
    *,
    intent_v2: str,
) -> dict[str, Any]:
    priority = DOMAIN_PRIORITY.get(intent_v2) or DOMAIN_PRIORITY["Unknown"]
    rank_index = {d: i for i, d in enumerate(priority)}
    items = list(classified.get("items") or [])

    def sort_key(item: dict[str, Any]) -> tuple:
        domain = str(item.get("domain") or "Other")
        return (
            rank_index.get(domain, 100),
            -float(item.get("rank_score") or 0),
            str(item.get("evidence_id") or ""),
        )

    ordered = sorted(items, key=sort_key)
    for i, item in enumerate(ordered):
        item["assembly_rank"] = i + 1
        item["priority_domain_index"] = rank_index.get(str(item.get("domain")), 100)

    # Framework inputs — top items per critical domains for this intent
    framework_inputs: dict[str, list[str]] = {}
    for domain in priority[:6]:
        ids = [x["evidence_id"] for x in ordered if x.get("domain") == domain and x.get("evidence_id")]
        if ids:
            framework_inputs[domain] = ids[:5]

    return {
        "stage": "evidence_ordering",
        "intent_v2": intent_v2,
        "priority_domains": list(priority),
        "ordered": ordered,
        "framework_inputs": framework_inputs,
        "top_evidence_ids": [x.get("evidence_id") for x in ordered[:12]],
        "fabricated": False,
    }
