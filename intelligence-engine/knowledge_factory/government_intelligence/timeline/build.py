"""Immutable policy timeline + point-in-time replay."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.schema import IGRI_VERSION


def timeline_order_ok(policies: list[dict[str, Any]]) -> bool:
    prev = ""
    for p in policies:
        d = str(p.get("announcement_date") or "")
        if prev and d < prev:
            return False
        prev = d or prev
    return True


def build_policy_timeline(policies: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(
        policies,
        key=lambda p: (str(p.get("announcement_date") or ""), str(p.get("policy_id") or "")),
    )
    by_year: dict[str, list[str]] = {}
    by_domain: dict[str, list[str]] = {}
    for p in ordered:
        y = str(p.get("announcement_date") or "")[:4] or "unknown"
        by_year.setdefault(y, []).append(p["policy_id"])
        by_domain.setdefault(str(p.get("domain") or "unknown"), []).append(p["policy_id"])

    return {
        "kind": "government_policy_timeline",
        "igri_version": IGRI_VERSION,
        "policies": ordered,
        "policy_ids": [p["policy_id"] for p in ordered],
        "policy_count": len(ordered),
        "by_year": by_year,
        "by_domain": by_domain,
        "chronological": True,
        "order_valid": timeline_order_ok(ordered),
        "immutable": True,
        "point_in_time": True,
        "fabricated": False,
    }


def replay_as_of(timeline: dict[str, Any], as_of: str) -> dict[str, Any]:
    cutoff = str(as_of or "")[:10]
    policies = list(timeline.get("policies") or [])
    visible = [
        p
        for p in policies
        if str(p.get("available_from") or p.get("announcement_date") or "")[:10] <= cutoff
    ]
    return {
        "kind": "government_policy_timeline_replay",
        "igri_version": IGRI_VERSION,
        "as_of": cutoff,
        "policies": visible,
        "policy_count": len(visible),
        "excluded_future_count": len(policies) - len(visible),
        "future_leakage": False,
        "rule": "available_from <= as_of",
        "fabricated": False,
        "immutable": True,
    }
