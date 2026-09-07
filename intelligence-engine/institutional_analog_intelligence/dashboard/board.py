"""IMAI Mission Control board metrics."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.registry.index import list_memories, type_counts
from institutional_analog_intelligence.schema import IMAI_VERSION, MODULE_CODE, REGIMES
from institutional_analog_intelligence.store import list_records


def build_board() -> dict[str, Any]:
    memories = list_memories()
    records = list_records(limit=200)
    hits = sum(1 for r in records if r.get("have_we_seen_this_before"))
    quality_pass = sum(1 for r in records if r.get("quality_status") == "pass")
    confs: list[float] = []
    for m in memories:
        c = m.get("confidence")
        if isinstance(c, (int, float)):
            confs.append(float(c))
    # Approximate analog accuracy proxy from retrieval audit hit rate
    analog_accuracy = round(hits / len(records), 3) if records else None
    regimes_covered = sorted(
        {r for m in memories for r in (m.get("macro_regime") or []) if r in REGIMES}
    )
    replay_capable = sum(1 for m in memories if m.get("available_from") and m.get("evidence_ids"))
    return {
        "module": MODULE_CODE,
        "version": IMAI_VERSION,
        "memory_hits": hits,
        "retrieval_audits": len(records),
        "analog_accuracy": analog_accuracy,
        "regime_coverage": len(regimes_covered),
        "regimes_covered": regimes_covered,
        "historical_coverage": len(memories),
        "replay_coverage": replay_capable,
        "similarity_scores_note": "Per-query similarity attached at retrieval time (0–100)",
        "memory_confidence_mean": round(sum(confs) / len(confs), 3) if confs else None,
        "counts_by_type": type_counts(),
        "quality_pass_rate": round(quality_pass / len(records), 3) if records else None,
        "recent": records[:12],
        "freeze": {
            "reasoning_engine": "frozen",
            "knowledge_factory": "frozen",
            "governance": "frozen",
            "institutional_learning_memory_ilm": "untouched",
        },
    }
