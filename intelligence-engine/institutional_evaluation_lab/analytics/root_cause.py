"""Failure intelligence scaffolding — cluster root causes from suite runs."""

from __future__ import annotations

from typing import Any


def cluster_failures(scored_rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [r for r in scored_rows if not r.get("passed")]
    clusters: dict[str, dict[str, Any]] = {}
    for r in failures:
        causes = r.get("root_causes") or ["unspecified"]
        primary = str(causes[0])
        bucket = clusters.setdefault(
            primary,
            {
                "root_cause": primary,
                "count": 0,
                "severity": "high" if primary in {
                    "future_leakage",
                    "fabricated_or_invented",
                    "quality_gate_fail",
                } else "medium",
                "question_ids": [],
                "categories": {},
                "status": "open",
                "owner": "quality_programme",
            },
        )
        bucket["count"] += 1
        if len(bucket["question_ids"]) < 25:
            bucket["question_ids"].append(r.get("question_id"))
        cat = str(r.get("category") or "unknown")
        bucket["categories"][cat] = bucket["categories"].get(cat, 0) + 1
    ranked = sorted(clusters.values(), key=lambda x: (-x["count"], x["root_cause"]))
    return {
        "n_failures": len(failures),
        "n_clusters": len(ranked),
        "top_20": ranked[:20],
        "note": "Legacy IEL cause tally — prefer root_cause_intelligence (RCI) for clustered fixes.",
    }
