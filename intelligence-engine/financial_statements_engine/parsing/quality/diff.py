"""Draft diff engine — old vs new canonical drafts."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.util import now_iso


def _metric_map(draft: dict[str, Any]) -> dict[str, Any]:
    """Extract metric → normalized_value from a parse result / draft payload."""
    out: dict[str, Any] = {}
    mapped = (draft.get("mapped") or {}).get("metrics") or {}
    for k, v in mapped.items():
        if isinstance(v, dict):
            out[k] = v.get("normalized_value")
        else:
            out[k] = v
    # also from drafts facts
    for d in draft.get("drafts") or []:
        for fact in d.get("facts") or []:
            out[str(fact.get("metric"))] = fact.get("normalized_value")
    return out


def diff_drafts(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    old_m = _metric_map(old or {})
    new_m = _metric_map(new)
    old_keys = set(old_m)
    new_keys = set(new_m)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed_values = []
    for k in sorted(old_keys & new_keys):
        if old_m.get(k) != new_m.get(k):
            changed_values.append({"metric": k, "old": old_m.get(k), "new": new_m.get(k)})

    old_labels = set(((old or {}).get("mapped") or {}).get("unknown_fields") or {})
    new_labels = set((new.get("mapped") or {}).get("unknown_fields") or {})
    # source fields
    old_src = {
        str((v or {}).get("source_field"))
        for v in (((old or {}).get("mapped") or {}).get("metrics") or {}).values()
        if isinstance(v, dict)
    }
    new_src = {
        str((v or {}).get("source_field"))
        for v in ((new.get("mapped") or {}).get("metrics") or {}).values()
        if isinstance(v, dict)
    }

    old_hier = (old or {}).get("hierarchy_fingerprint") or ((old or {}).get("hierarchy") or {}).get("hierarchy_fingerprint")
    new_hier = new.get("hierarchy_fingerprint") or (new.get("hierarchy") or {}).get("hierarchy_fingerprint")

    old_conf = (old or {}).get("confidence") or {}
    new_conf = new.get("confidence") or {}

    return {
        "added_metrics": added,
        "removed_metrics": removed,
        "changed_values": changed_values,
        "changed_labels": {
            "added_source_fields": sorted(new_src - old_src),
            "removed_source_fields": sorted(old_src - new_src),
            "unknown_added": sorted(new_labels - old_labels),
            "unknown_removed": sorted(old_labels - new_labels),
        },
        "changed_structure": old_hier != new_hier,
        "hierarchy_fingerprint_old": old_hier,
        "hierarchy_fingerprint_new": new_hier,
        "confidence_changes": {
            "old": old_conf,
            "new": new_conf,
            "overall_delta": (new_conf.get("overall") or 0) - (old_conf.get("overall") or 0)
            if isinstance(new_conf, dict) and isinstance(old_conf, dict)
            else None,
        },
        "as_of": now_iso(),
        "layer": "diff_engine",
    }
