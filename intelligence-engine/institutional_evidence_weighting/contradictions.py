"""Identify relative weight of conflicting evidence — do NOT resolve (Sprint 4.3)."""

from __future__ import annotations

from typing import Any


def _topic_key(w: dict[str, Any]) -> str:
    title = str(w.get("title") or "").strip().lower()
    # Prefer entity+coarse title token
    entity = ""
    # evidence_id prefix often encodes topic
    eid = str(w.get("evidence_id") or "")
    if title:
        # first 48 chars normalised
        return title[:48]
    return eid or "unknown"


def identify_conflicts(weighted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Pairwise flag when two eligible items share a topic key but differ in source tier
    or have large weight gaps — label higher/lower/equal only.
    """
    eligible = [w for w in weighted if w.get("eligible") is not False]
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for w in eligible:
        by_topic.setdefault(_topic_key(w), []).append(w)

    conflicts: list[dict[str, Any]] = []
    for topic, items in by_topic.items():
        if len(items) < 2:
            continue
        # Only mark conflict when sources disagree across credibility bands
        sources = {str(i.get("source")) for i in items}
        if len(sources) < 2:
            continue
        ordered = sorted(items, key=lambda x: (-float(x.get("weight_score") or 0), str(x.get("evidence_id"))))
        top = ordered[0]
        for other in ordered[1:]:
            a = float(top.get("weight_score") or 0)
            b = float(other.get("weight_score") or 0)
            if abs(a - b) < 0.01:
                relation = "equal_weight"
            elif a > b:
                relation = "higher_weight"
            else:
                relation = "lower_weight"
            conflicts.append(
                {
                    "topic": topic,
                    "a_evidence_id": top.get("evidence_id"),
                    "b_evidence_id": other.get("evidence_id"),
                    "a_weight": a,
                    "b_weight": b,
                    "a_source": top.get("source"),
                    "b_source": other.get("source"),
                    "relation_a_vs_b": relation,
                    "resolved": False,
                    "note": "Contradiction Resolution deferred to Sprint 4.3",
                }
            )
    return conflicts
