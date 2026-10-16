"""Structured user feedback → improvement backlog (L-01)."""

from __future__ import annotations

import threading
import uuid
from collections import Counter, deque
from typing import Any, Deque, List, Optional

from institutional_launch.schema import FEEDBACK_REACTIONS, FEEDBACK_TAGS

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


_LOCK = threading.Lock()
_FEEDBACK: Deque[dict[str, Any]] = deque(maxlen=5000)


def reset_for_tests() -> None:
    with _LOCK:
        _FEEDBACK.clear()


def submit_feedback(
    *,
    screen: str,
    reaction: str,
    comment: str = "",
    tags: Optional[List[str]] = None,
    user_id: str = "",
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    react = str(reaction or "").strip().lower().replace(" ", "_")
    if react in {"👍", "up", "yes", "good"}:
        react = "helpful"
    if react in {"👎", "down", "no", "bad"}:
        react = "not_helpful"
    if react not in FEEDBACK_REACTIONS:
        return {"ok": False, "error": f"reaction must be one of {FEEDBACK_REACTIONS}"}

    clean_tags = [t for t in (tags or []) if t in FEEDBACK_TAGS]
    # Infer tags from free text
    text = (comment or "").lower()
    for tag in FEEDBACK_TAGS:
        if tag.replace("_", " ") in text or tag in text:
            if tag not in clean_tags:
                clean_tags.append(tag)

    row = {
        "feedback_id": f"fb_{uuid.uuid4().hex[:12]}",
        "screen": str(screen or "unknown"),
        "reaction": react,
        "comment": (comment or "").strip()[:2000],
        "tags": clean_tags,
        "user_id": user_id or "anonymous",
        "timestamp": now_iso(),
        "meta": dict(meta or {}),
        "backlog_candidate": react == "not_helpful" or bool(clean_tags),
    }
    with _LOCK:
        _FEEDBACK.append(row)
    return {"ok": True, **row}


def recent_feedback(limit: int = 40) -> List[dict[str, Any]]:
    with _LOCK:
        rows = list(_FEEDBACK)[-limit:]
    return list(reversed(rows))


def feedback_summary() -> dict[str, Any]:
    with _LOCK:
        rows = list(_FEEDBACK)
    helpful = sum(1 for r in rows if r.get("reaction") == "helpful")
    not_helpful = sum(1 for r in rows if r.get("reaction") == "not_helpful")
    total = len(rows)
    tag_counts = Counter()
    for r in rows:
        tag_counts.update(r.get("tags") or [])
    backlog = [r for r in rows if r.get("backlog_candidate")]
    return {
        "total": total,
        "helpful": helpful,
        "not_helpful": not_helpful,
        "helpful_rate": round(helpful / total, 4) if total else None,
        "tag_counts": dict(tag_counts),
        "backlog_count": len(backlog),
        "recent": recent_feedback(8),
        "allowed_tags": list(FEEDBACK_TAGS),
    }
