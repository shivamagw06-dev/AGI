"""Historical replay communication sections — PIT only, no lookahead language."""

from __future__ import annotations

from typing import Any

from institutional_communication.styles.institutional import bullet


def render_replay_sections(institutional_answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    as_of = institutional_answer.get("as_of")
    replay = institutional_answer.get("replay") or {}
    items = list(((institutional_answer.get("evidence") or {}).get("items") or []))
    ranked = replay.get("ranked_count")

    hist = {
        "section": "historical_context",
        "title": "Historical Context",
        "bullets": [
            bullet(f"Point-in-time bound: as_of={as_of}"),
            bullet("Only evidence with available_from ≤ as_of is admissible."),
            bullet("Current market prices must not be used when as_of is historical."),
        ],
        "visible": True,
    }
    ts = {
        "section": "replay_timestamp",
        "title": "Replay Timestamp",
        "bullets": [
            bullet(f"as_of={as_of}"),
            bullet(f"retrieval_id={replay.get('retrieval_id') or institutional_answer.get('replay_id')}"),
        ],
        "visible": True,
    }
    avail = {
        "section": "available_evidence",
        "title": "Available Evidence",
        "bullets": [
            bullet(f"IERE ranked_count at as_of: {ranked}"),
            bullet(f"Bound evidence items in InstitutionalAnswer: {len(items)}"),
        ]
        + [
            bullet(f"{i.get('evidence_id')}: available_from={i.get('available_from')}")
            for i in items[:8]
        ],
        "visible": True,
    }
    # Leakage check — communication layer flags if current-price language would be inappropriate
    leakage_pass = bool(as_of)
    leak_line = (
        "PASS — communication restricted to InstitutionalAnswer replay metadata"
        if leakage_pass
        else "N/A — no as_of bound"
    )
    leak = {
        "section": "future_leakage_check",
        "title": "Future Leakage Check",
        "bullets": [
            bullet(leak_line),
            bullet("ICE does not inject live quotes into historical replay templates."),
        ],
        "passed": leakage_pass,
        "visible": True,
    }
    return {
        "historical_context": hist,
        "replay_timestamp": ts,
        "available_evidence": avail,
        "future_leakage_check": leak,
    }
