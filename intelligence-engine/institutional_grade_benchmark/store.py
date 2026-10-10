"""In-memory store for panel scores and recorded evaluations."""

from __future__ import annotations

from typing import Any

_PANEL: dict[str, Any] = {
    "blind_votes": [],
    "productivity": {},
    "manual_section_scores": {},
    "notes": [],
}


def reset_for_tests() -> None:
    _PANEL["blind_votes"] = []
    _PANEL["productivity"] = {}
    _PANEL["manual_section_scores"] = {}
    _PANEL["notes"] = []


def record_blind_vote(
    *,
    analyst_id: str,
    preferred_label: str,
    ranking: list[str] | None = None,
    comment: str = "",
) -> dict[str, Any]:
    row = {
        "analyst_id": str(analyst_id or "anonymous"),
        "preferred_label": str(preferred_label or ""),
        "ranking": list(ranking or []),
        "comment": str(comment or ""),
    }
    _PANEL["blind_votes"].append(row)
    return {"ok": True, "vote": row, "total_votes": len(_PANEL["blind_votes"])}


def blind_votes() -> list[dict[str, Any]]:
    return list(_PANEL["blind_votes"])


def record_productivity(
    *,
    group: str,
    completion_time_min: float,
    confidence: float,
    quality: float,
    n_analysts: int = 1,
) -> dict[str, Any]:
    g = str(group or "").strip().lower()
    _PANEL["productivity"][g] = {
        "group": g,
        "completion_time_min": float(completion_time_min),
        "confidence": float(confidence),
        "quality": float(quality),
        "n_analysts": int(n_analysts),
    }
    return {"ok": True, "productivity": dict(_PANEL["productivity"])}


def productivity() -> dict[str, Any]:
    return dict(_PANEL["productivity"])


def set_manual_section_score(section_key: str, score: float, max_score: float) -> None:
    _PANEL["manual_section_scores"][section_key] = {
        "score": float(score),
        "max": float(max_score),
    }


def manual_section_scores() -> dict[str, Any]:
    return dict(_PANEL["manual_section_scores"])


def panel_complete() -> bool:
    """Blind panel + both productivity groups recorded."""
    votes = _PANEL["blind_votes"]
    prod = _PANEL["productivity"]
    return len(votes) >= 3 and "bloomberg" in prod and "agib" in prod
