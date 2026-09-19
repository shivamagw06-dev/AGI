"""Versioned thesis evolution records for Institutional Learning Memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_evolution(
    *,
    current_conviction: float,
    status: str,
    core_thesis: str,
    prior_snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    prior = [p for p in (prior_snapshots or []) if isinstance(p, dict)]
    previous = prior[-1] if prior else {}
    previous_conviction = previous.get("conviction")
    if isinstance(previous_conviction, dict):
        previous_conviction = previous_conviction.get("overall")
    delta = (
        round(float(current_conviction) - float(previous_conviction), 4)
        if previous_conviction is not None
        else 0.0
    )
    if not prior:
        change_type = "Created"
    elif delta >= 0.04:
        change_type = "Conviction Improved"
    elif delta <= -0.04:
        change_type = "Conviction Weakened"
    elif previous.get("status") != status:
        change_type = "State Changed"
    else:
        change_type = "Reaffirmed"

    current = {
        "version": len(prior) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "change_type": change_type,
        "conviction": round(float(current_conviction), 4),
        "status": status,
        "core_thesis": core_thesis,
        "delta": delta,
    }
    history = [
        {
            "version": p.get("version", i + 1),
            "timestamp": p.get("timestamp") or p.get("generated_at"),
            "change_type": p.get("change_type") or "Prior Snapshot",
            "conviction": (
                (p.get("conviction") or {}).get("overall")
                if isinstance(p.get("conviction"), dict)
                else p.get("conviction")
            ),
            "status": p.get("status"),
            "core_thesis": (
                (p.get("core_thesis") or {}).get("statement")
                if isinstance(p.get("core_thesis"), dict)
                else p.get("core_thesis")
            ),
        }
        for i, p in enumerate(prior[-11:])
    ] + [current]
    return {
        "current_version": current["version"],
        "change_type": change_type,
        "conviction_delta": delta,
        "history": history,
        "ilm_payload": {
            "feed_into": "ILM",
            "event": "thesis_evolution",
            "version": current["version"],
            "change_type": change_type,
        },
    }
