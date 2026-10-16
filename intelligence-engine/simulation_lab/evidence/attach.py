"""Attach evidence references to simulation assumptions."""

from __future__ import annotations

from typing import Any


def attach_evidence(assumptions: dict[str, Any]) -> dict[str, Any]:
    items = list(assumptions.get("evidence") or [])
    # Soft institutional layer tags — no provider redesign
    layered = []
    for e in items:
        text = str(e)
        layer = "general"
        upper = text.upper()
        for tag in ("FIL", "FDI", "MII", "ACI", "EIL", "PIL", "CIG", "IKG", "FIE", "ILM"):
            if tag in upper or tag.lower() in text.lower():
                layer = tag
                break
        layered.append({"ref": text, "layer": layer})
    return {
        "items": layered,
        "count": len(layered),
        "unsupported_deterministic_outcomes": False,
        "rule": "Evidence attached to assumptions — outcomes remain probabilistic",
    }
