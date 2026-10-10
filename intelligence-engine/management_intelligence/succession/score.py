"""Succession / key-person stability."""

from __future__ import annotations

from typing import Any


def succession_score(raw: dict[str, Any] | None) -> dict[str, Any]:
    r = dict(raw or {})
    score = float(r.get("score", 65))
    kpr = str(r.get("key_person_risk") or "moderate")
    if kpr in {"low", "low_moderate"}:
        score = max(score, 75)
    elif kpr == "high":
        score = min(score, 45)
    return {
        "succession": round(score, 1),
        "ceo_stability": r.get("ceo_stability"),
        "cfo_stability": r.get("cfo_stability"),
        "key_person_risk": kpr,
        "succession_planning": r.get("succession_planning"),
    }
