"""Produce registries + policy objects from soft context."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.objects.policy import build_policy, policy_fingerprint


def produce_bodies(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    bodies = []
    for row in list(ctx.get("ministries") or []) + list(ctx.get("regulators") or []):
        bodies.append(
            {
                **row,
                "immutable": True,
                "fabricated": False,
                "political_opinion": False,
                "provenance": {
                    "source": "institutional_registry",
                    "collector": "igri.collectors.registry",
                    "confidence": 0.95,
                    "derived_from": ["ministry_registry" if row.get("kind") in {"ministry", "department", "government"} else "regulators"],
                    "fabricated": False,
                },
            }
        )
    return bodies


def produce_policies(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for seed in ctx.get("policy_seeds") or []:
        pol = build_policy(seed)
        fp = pol["fingerprint"]
        if fp in seen or pol["policy_id"] in seen:
            continue
        seen.add(fp)
        seen.add(pol["policy_id"])
        out.append(pol)
    out.sort(key=lambda p: (p.get("announcement_date") or "", p.get("policy_id") or ""))
    return out


def produce_all(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "bodies": produce_bodies(ctx),
        "policies": produce_policies(ctx),
    }
