"""Communication quality — transparency, consistency, tone, risk acknowledgement."""

from __future__ import annotations

from typing import Any


def communication_score(comm: dict[str, Any] | None, *, fdi_optimism: str | None = None) -> dict[str, Any]:
    c = dict(comm or {})
    keys = (
        "transparency",
        "consistency",
        "clarity",
        "risk_acknowledgement",
        "guidance_stability",
    )
    vals = [float(c.get(k, 60)) for k in keys]
    overconf = float(c.get("overconfidence", 40))
    # lower overconfidence is better
    composite = round((sum(vals) / len(vals)) * 0.85 + (100.0 - overconf) * 0.15, 1)
    if fdi_optimism == "optimism_decreased":
        # acknowledging pressure can raise risk acknowledgement
        composite = min(100.0, composite + 2.0)
        c["tone_shift"] = "more_cautious"
    return {
        "communication": composite,
        "components": {k: c.get(k) for k in keys},
        "overconfidence": overconf,
        "tone": c.get("tone"),
        "notes": c.get("notes"),
        "tone_shift": c.get("tone_shift"),
    }
