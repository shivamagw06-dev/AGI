"""Consensus engine — pick canonical value from multi-provider observations."""

from __future__ import annotations

from typing import Any

from dvc.models import make_validated_field
from dvc.priority import base_confidence, provider_priority


def _numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def consensus_for_field(
    field: str,
    observations: list[dict[str, Any]],
    *,
    symbol: str,
    previous_value: Any = None,
    relative_tolerance: float = 0.005,
) -> dict[str, Any]:
    """
    observations: [{provider, value, timestamp?, latency_ms?}, ...]
    Returns ValidatedField dict.
    """
    usable = [o for o in observations if o.get("value") is not None and o.get("provider")]
    if not usable:
        return make_validated_field(
            field=field,
            value=None,
            provider="none",
            confidence=0.0,
            symbol=symbol,
            previous_value=previous_value,
            reason="no_observations",
            validation_status="missing",
            observations=observations,
        )

    # Prefer numeric consensus when all numeric
    nums = [(o, _numeric(o.get("value"))) for o in usable]
    if all(n is not None for _, n in nums):
        return _numeric_consensus(field, usable, symbol=symbol, previous_value=previous_value, tol=relative_tolerance)

    # Categorical / string — highest priority wins; agreement boosts confidence
    ordered = sorted(usable, key=lambda o: provider_priority(str(o.get("provider"))))
    winner = ordered[0]
    win_val = winner.get("value")
    agreeing = [o for o in usable if str(o.get("value")).strip().lower() == str(win_val).strip().lower()]
    rejected = [str(o.get("provider")) for o in usable if o not in agreeing]
    conf = base_confidence(str(winner.get("provider")))
    if len(agreeing) > 1:
        conf = min(0.995, conf + 0.02 * (len(agreeing) - 1))
    if rejected:
        conf = max(0.55, conf - 0.03 * len(rejected))
    fallback = ordered[1]["provider"] if len(ordered) > 1 else None
    return make_validated_field(
        field=field,
        value=win_val,
        provider=str(winner.get("provider")),
        confidence=conf,
        symbol=symbol,
        fallback_provider=str(fallback) if fallback else None,
        previous_value=previous_value,
        rejected_providers=rejected,
        reason="priority_with_agreement" if len(agreeing) > 1 else "priority_winner",
        observations=usable,
        validation_status="validated" if not rejected else "validated_with_dissent",
    )


def _numeric_consensus(
    field: str,
    usable: list[dict[str, Any]],
    *,
    symbol: str,
    previous_value: Any,
    tol: float,
) -> dict[str, Any]:
    ordered = sorted(usable, key=lambda o: provider_priority(str(o.get("provider"))))
    winner = ordered[0]
    win_val = float(_numeric(winner.get("value")) or 0.0)
    agreeing = []
    rejected = []
    for o in usable:
        v = float(_numeric(o.get("value")) or 0.0)
        denom = abs(win_val) if win_val != 0 else 1.0
        rel = abs(v - win_val) / denom
        if rel <= tol or abs(v - win_val) < 1e-9:
            agreeing.append(o)
        else:
            rejected.append(str(o.get("provider")))

    conf = base_confidence(str(winner.get("provider")))
    if len(agreeing) > 1:
        conf = min(0.995, conf + 0.025 * (len(agreeing) - 1))
    if rejected:
        # Larger disagreement → lower confidence
        spreads = []
        for o in usable:
            v = float(_numeric(o.get("value")) or 0.0)
            denom = abs(win_val) if win_val != 0 else 1.0
            spreads.append(abs(v - win_val) / denom)
        max_spread = max(spreads) if spreads else 0.0
        conf = max(0.40, conf - min(0.35, max_spread * 2))

    fallback = None
    for o in ordered[1:]:
        if str(o.get("provider")) not in rejected:
            fallback = o.get("provider")
            break
    if fallback is None and len(ordered) > 1:
        fallback = ordered[1].get("provider")

    return make_validated_field(
        field=field,
        value=win_val,
        provider=str(winner.get("provider")),
        confidence=conf,
        symbol=symbol,
        fallback_provider=str(fallback) if fallback else None,
        previous_value=previous_value,
        rejected_providers=rejected,
        reason="numeric_priority_consensus",
        observations=usable,
        validation_status="validated" if not rejected else "validated_with_conflict",
    )
