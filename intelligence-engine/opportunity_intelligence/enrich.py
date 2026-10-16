"""Soft-attach Opportunity Intelligence into CID — read-only, no DE mutation."""

from __future__ import annotations

from typing import Any


def merge_opportunity_into_dossier(dossier: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(dossier, dict) or not isinstance(pack, dict) or not pack.get("ok"):
        return dossier
    out = dict(dossier)
    opp = pack.get("opportunity") if isinstance(pack.get("opportunity"), dict) else {}

    out["opportunity_intelligence"] = {
        "enabled": True,
        "ok": True,
        "engine": pack.get("engine"),
        "version": pack.get("version"),
        "workstream_id": pack.get("workstream_id"),
        "entity": pack.get("entity"),
        "score": pack.get("score"),
        "confidence": pack.get("confidence"),
        "research_priority": pack.get("research_priority"),
        "why_now": pack.get("why_now"),
        "strengths": pack.get("strengths") or [],
        "blockers": [
            {"code": b.get("code"), "severity": b.get("severity"), "title": b.get("title")}
            for b in (pack.get("blockers") or [])[:8]
        ],
        "catalysts": [
            {
                "name": c.get("name"),
                "expected_window": c.get("expected_window"),
                "importance": c.get("importance"),
                "confidence": c.get("confidence"),
            }
            for c in (pack.get("catalysts") or [])[:8]
        ],
        "evidence_strength": {
            "dimension_coverage_avg": _avg_coverage(pack.get("dimensions") or {}),
            "n_evidence": len((opp.get("evidence") or pack.get("opportunity", {}).get("evidence") or [])),
        },
        "freshness": pack.get("freshness"),
        "recommendation_policy": pack.get("recommendation_policy"),
        "issues_recommendations": False,
    }

    evidence = list(out.get("evidence") or [])
    evidence.append(
        {
            "evidence_type": "opportunity_intelligence",
            "source_id": pack.get("engine"),
            "ticker": pack.get("entity"),
            "payload": {
                "score": pack.get("score"),
                "research_priority": pack.get("research_priority"),
                "why_now": pack.get("why_now"),
                "confidence": pack.get("confidence"),
            },
            "confidence": (float(pack.get("confidence") or 0) / 100.0)
            if (pack.get("confidence") or 0) > 1
            else float(pack.get("confidence") or 0.7),
        }
    )
    out["evidence"] = evidence[-200:]
    return out


def _avg_coverage(dimensions: dict[str, Any]) -> float | None:
    vals = []
    for d in dimensions.values():
        if isinstance(d, dict) and d.get("coverage") is not None:
            try:
                vals.append(float(d["coverage"]))
            except (TypeError, ValueError):
                pass
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)
