"""ICE dashboard metrics for Mission Control."""

from __future__ import annotations

from collections import Counter
from typing import Any

from institutional_communication import store
from institutional_communication.schema import ICE_VERSION, PROGRAMME


def communication_dashboard() -> dict[str, Any]:
    rows = store.list_rows(limit=500)
    templates: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    fw_vis = 0
    complete = 0
    generic = 0
    conf_quality = 0
    for r in rows:
        templates[str(r.get("template") or "n/a")] += 1
        styles[str(r.get("narrative_style") or "n/a")] += 1
        if r.get("framework_visible"):
            fw_vis += 1
        if float(r.get("narrative_completeness") or 0) >= 0.99:
            complete += 1
        if r.get("generic_template") or any(
            str(f).startswith("generic_template") for f in (r.get("failures") or [])
        ):
            generic += 1
        if r.get("validation_passed"):
            conf_quality += 1
    n = len(rows) or 1
    return {
        "programme": PROGRAMME,
        "ice_version": ICE_VERSION,
        "communication_count": len(rows),
        "communication_style": dict(styles),
        "template_used": dict(templates.most_common()),
        "framework_visibility": {"count": fw_vis, "rate": round(fw_vis / n, 4)},
        "citation_density": {
            "high": sum(1 for r in rows if r.get("citation_density") == "high"),
            "moderate": sum(1 for r in rows if r.get("citation_density") == "moderate"),
            "low": sum(1 for r in rows if r.get("citation_density") == "low"),
        },
        "narrative_completeness": {
            "complete": complete,
            "rate": round(complete / n, 4),
        },
        "confidence_quality": {
            "gate_pass": conf_quality,
            "rate": round(conf_quality / n, 4),
        },
        "generic_template_rate": round(generic / n, 4),
        "recent": rows[:20],
        "fabricated": False,
    }
