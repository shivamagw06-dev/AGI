"""Quality engine — reject OCR errors, duplicates, conflicts, missing units."""

from __future__ import annotations

from typing import Any


def validate_facts(facts: list[dict[str, Any]]) -> dict[str, Any]:
    rejected = []
    kept = []
    seen = set()
    conflicts = []

    # detect conflicts: same ticker/metric/period different values
    index: dict[str, list[dict[str, Any]]] = {}
    for f in facts:
        key = f"{f.get('ticker')}|{f.get('metric')}|{f.get('period')}"
        index.setdefault(key, []).append(f)

    for key, group in index.items():
        nums = [g for g in group if isinstance(g.get("value"), (int, float))]
        if len({round(float(g["value"]), 6) for g in nums}) > 1:
            conflicts.append({"key": key, "values": [g["value"] for g in nums]})

    for f in facts:
        reasons = []
        if f.get("unit") in (None, "") and f.get("category") == "financial" and isinstance(f.get("value"), (int, float)):
            reasons.append("missing_units")
        if isinstance(f.get("value"), float) and (f["value"] != f["value"]):  # NaN
            reasons.append("ocr_error")
        dup_key = f"{f.get('ticker')}|{f.get('metric')}|{f.get('period')}|{f.get('value')}|{f.get('doc_id')}"
        if dup_key in seen:
            reasons.append("duplicate_fact")
        seen.add(dup_key)
        conf_key = f"{f.get('ticker')}|{f.get('metric')}|{f.get('period')}"
        if any(c["key"] == conf_key for c in conflicts):
            # keep best tier, mark others
            group = index[conf_key]
            best = min(group, key=lambda g: int(g.get("evidence_tier") or 99))
            if f is not best and f.get("fact_id") != best.get("fact_id"):
                reasons.append("conflicting_metrics")

        if reasons:
            rejected.append({**f, "reject_reasons": reasons, "validation_status": "rejected"})
        else:
            kept.append(f)

    return {
        "kept": kept,
        "rejected": rejected,
        "conflicts": conflicts,
        "counts": {
            "input": len(facts),
            "kept": len(kept),
            "rejected": len(rejected),
            "conflicts": len(conflicts),
        },
    }
