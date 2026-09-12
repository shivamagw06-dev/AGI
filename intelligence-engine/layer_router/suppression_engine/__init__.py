"""Suppress layers below importance threshold / never modes."""

from __future__ import annotations

from typing import Any

from layer_router.schema import REGISTERED_LAYERS, SUPPRESSION_IMPORTANCE_THRESHOLD


def suppress_layers(
    importance: dict[str, int],
    *,
    force_required: list[str] | None = None,
    force_optional: list[str] | None = None,
    threshold: int = SUPPRESSION_IMPORTANCE_THRESHOLD,
) -> dict[str, Any]:
    required = list(force_required or [])
    optional = list(force_optional or [])
    selected = set(required) | set(optional)
    suppressed = []
    for layer in REGISTERED_LAYERS:
        if layer in selected:
            continue
        score = int(importance.get(layer, 0))
        if score < threshold:
            suppressed.append(layer)
        elif layer not in optional and score >= threshold:
            # Conditional — available but not forced
            optional.append(layer)
            selected.add(layer)
    # Clean optional that are required
    optional = [x for x in optional if x not in required]
    suppressed = [x for x in REGISTERED_LAYERS if x not in set(required) | set(optional)]
    return {
        "required_layers": required,
        "optional_layers": optional,
        "suppressed_layers": suppressed,
        "threshold": threshold,
        "no_placeholders": True,
        "no_empty_cards": True,
    }
