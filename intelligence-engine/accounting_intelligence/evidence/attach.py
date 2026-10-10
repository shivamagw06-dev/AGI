"""Attach evidence refs — no opinion without filing hook."""

from __future__ import annotations

from typing import Any


def evidence_pack(profile: dict[str, Any], *, confidence: dict[str, Any]) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    for obs in profile.get("observations") or []:
        if isinstance(obs, dict):
            refs.append(
                {
                    "claim": obs.get("claim"),
                    "period": obs.get("period"),
                    "domain": obs.get("domain"),
                    "evidence_doc": obs.get("evidence_doc"),
                    "evidence_tier": obs.get("evidence_tier"),
                    "metric": obs.get("metric"),
                    "value": obs.get("value"),
                }
            )
    for p in profile.get("policies") or []:
        if isinstance(p, dict) and p.get("evidence_doc"):
            refs.append(
                {
                    "claim": p.get("description"),
                    "period": p.get("period"),
                    "domain": "policy",
                    "evidence_doc": p.get("evidence_doc"),
                    "evidence_tier": 2,
                }
            )
    return {
        "count": len(refs),
        "refs": refs[:40],
        "rule": "No accounting opinion without evidence linked to a filing or disclosed metric",
        "coverage": confidence.get("evidence_coverage"),
        "missing": confidence.get("unknowns") or [],
    }
