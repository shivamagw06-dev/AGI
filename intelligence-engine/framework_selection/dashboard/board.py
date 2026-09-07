"""IFSE dashboard metrics."""

from __future__ import annotations

from collections import Counter
from typing import Any

from framework_selection.registry.frameworks import framework_ids
from framework_selection.schema import IFSE_VERSION, PROGRAMME
from framework_selection import store


def framework_dashboard() -> dict[str, Any]:
    rows = store.list_selections(limit=500)
    usage: Counter[str] = Counter()
    bands: Counter[str] = Counter()
    sectors: Counter[str] = Counter()
    multi = 0
    wrong = 0
    for r in rows:
        for fid in r.get("framework_ids") or []:
            usage[str(fid)] += 1
        bands[str(r.get("confidence") or "n/a")] += 1
        sectors[str(r.get("sector") or "n/a")] += 1
        if r.get("multi_framework"):
            multi += 1
        fails = r.get("failures") or []
        if any(str(f).startswith("wrong_framework") or str(f).startswith("forbidden") for f in fails):
            wrong += 1

    n = len(rows) or 1
    return {
        "programme": PROGRAMME,
        "ifse_version": IFSE_VERSION,
        "selection_count": len(rows),
        "framework_usage": dict(usage.most_common()),
        "framework_coverage": {
            "registered": len(framework_ids()),
            "used": len(usage),
            "unused": sorted(set(framework_ids()) - set(usage)),
        },
        "multi_framework_usage": {
            "count": multi,
            "rate": round(multi / n, 4),
        },
        "wrong_framework_rate": round(wrong / n, 4),
        "confidence_distribution": dict(bands),
        "sector_distribution": dict(sectors),
        "framework_accuracy": {
            "passed": sum(1 for r in rows if r.get("validation_passed")),
            "failed": sum(1 for r in rows if not r.get("validation_passed")),
            "pass_rate": round(
                sum(1 for r in rows if r.get("validation_passed")) / n,
                4,
            ),
        },
        "recent": rows[:20],
        "fabricated": False,
    }
