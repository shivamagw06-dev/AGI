"""Revenue Recognition Engine."""

from __future__ import annotations

from typing import Any


def revenue_recognition(block: dict[str, Any] | None) -> dict[str, Any]:
    b = block or {}
    policy_change = bool(b.get("policy_change"))
    channel = str(b.get("channel_stuffing_risk") or "low").lower()
    early = str(b.get("early_recognition_risk") or "low").lower()

    score = 85.0
    flags: list[str] = []
    if policy_change:
        score -= 20
        flags.append("revenue_policy_change")
    if channel in {"high", "elevated"}:
        score -= 25
        flags.append("channel_stuffing_indicator")
    elif channel == "watch":
        score -= 10
    if "watch" in early or early == "high":
        score -= 12
        flags.append("early_revenue_recognition_watch")
    score = max(0.0, min(100.0, score))

    return {
        "revenue_recognition": round(score, 1),
        "policy": b.get("policy"),
        "policy_change": policy_change,
        "channel_stuffing_risk": channel,
        "early_recognition_risk": early,
        "flags": flags,
        "notes": b.get("notes"),
        "evidence_doc": b.get("evidence_doc"),
    }
