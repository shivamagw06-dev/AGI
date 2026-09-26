"""Institutional audit registry."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


def register_audit(
    question: str,
    audit_status: str,
    reasoning_score: float,
    replay_id: str,
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    raw = f"{question}|{audit_status}|{reasoning_score:.4f}|{replay_id}"
    return {
        "audit_id": f"IRAE-{hashlib.sha256(raw.encode()).hexdigest()[:12].upper()}",
        "created_at": created_at,
        "status": audit_status,
        "reasoning_score": reasoning_score,
        "replay_id": replay_id,
        "immutable": True,
        "certification_scope": [
            "Investment Committee",
            "Portfolio Intelligence Office",
            "Decision Engine V2",
            "CIO",
        ],
    }
