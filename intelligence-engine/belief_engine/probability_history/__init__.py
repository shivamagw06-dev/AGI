"""Probability history — track prior → evidence → posterior path per hypothesis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_history(
    *,
    hypothesis_id: str,
    prior: float,
    contributions: list[dict[str, Any]],
    posterior: float,
    belief_state: str,
) -> list[dict[str, Any]]:
    ts = datetime.now(timezone.utc).isoformat()
    hist = [
        {
            "ts": ts,
            "step": "prior",
            "probability": prior,
            "note": f"Prior belief for {hypothesis_id}",
        }
    ]
    running = prior
    # Reconstruct approximate path for transparency (display only)
    for c in contributions:
        llr = float(c.get("log_lr") or 0)
        # Approximate local move for ledger readability
        approx_delta = max(-0.2, min(0.2, llr * 0.08))
        running = round(max(0.05, min(0.95, running + approx_delta)), 4)
        hist.append(
            {
                "ts": ts,
                "step": "evidence_update",
                "evidence_id": c.get("evidence_id"),
                "effect": c.get("effect"),
                "log_lr": c.get("log_lr"),
                "probability": running,
                "note": c.get("text") or c.get("effect"),
            }
        )
    hist.append(
        {
            "ts": ts,
            "step": "posterior",
            "probability": posterior,
            "belief_state": belief_state,
            "note": f"Calibrated posterior belief → {belief_state}",
        }
    )
    return hist
