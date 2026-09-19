"""Materiality Policy — what institutional analysts actually care about.

Gates noise before Learning Events / Memory / Timeline are written.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MaterialityTier(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    IGNORE = "Ignore"


@dataclass(frozen=True)
class FieldPolicy:
    field_name: str
    category: str
    # Absolute thresholds in the field's native units (pp for growth/margins, abs for PE, pct for price/debt)
    ignore_below: float
    medium_at: float
    high_at: float
    unit: str  # "pp" | "abs" | "pct" | "event"


# Default India-equity institutional gates (Sprint 6.3)
DEFAULT_FIELD_POLICIES: dict[str, FieldPolicy] = {
    "pe_ratio": FieldPolicy("pe_ratio", "Valuation", ignore_below=1.0, medium_at=1.0, high_at=3.0, unit="abs"),
    "pe": FieldPolicy("pe", "Valuation", ignore_below=1.0, medium_at=1.0, high_at=3.0, unit="abs"),
    "price": FieldPolicy("price", "Market", ignore_below=3.0, medium_at=3.0, high_at=5.0, unit="pct"),
    "last_price": FieldPolicy("last_price", "Market", ignore_below=3.0, medium_at=3.0, high_at=5.0, unit="pct"),
    "revenue_growth": FieldPolicy(
        "revenue_growth", "Financial Performance", ignore_below=5.0, medium_at=5.0, high_at=8.0, unit="pp"
    ),
    "earnings_growth": FieldPolicy(
        "earnings_growth", "Financial Performance", ignore_below=5.0, medium_at=5.0, high_at=8.0, unit="pp"
    ),
    "pat_margin": FieldPolicy(
        "pat_margin", "Financial Performance", ignore_below=1.0, medium_at=1.0, high_at=2.0, unit="pp"
    ),
    "ebitda_margin": FieldPolicy(
        "ebitda_margin", "Financial Performance", ignore_below=1.0, medium_at=1.0, high_at=2.0, unit="pp"
    ),
    "debt": FieldPolicy("debt", "Financial Performance", ignore_below=10.0, medium_at=10.0, high_at=25.0, unit="pct"),
    "cash": FieldPolicy("cash", "Financial Performance", ignore_below=10.0, medium_at=10.0, high_at=25.0, unit="pct"),
    "promoters_pct": FieldPolicy("promoters_pct", "Ownership", ignore_below=1.0, medium_at=1.0, high_at=3.0, unit="pp"),
    "fii_pct": FieldPolicy("fii_pct", "Ownership", ignore_below=1.0, medium_at=1.0, high_at=3.0, unit="pp"),
    "dii_pct": FieldPolicy("dii_pct", "Ownership", ignore_below=1.0, medium_at=1.0, high_at=3.0, unit="pp"),
    "mutual_funds_pct": FieldPolicy(
        "mutual_funds_pct", "Ownership", ignore_below=1.0, medium_at=1.0, high_at=3.0, unit="pp"
    ),
    "target_price": FieldPolicy("target_price", "Valuation", ignore_below=5.0, medium_at=5.0, high_at=10.0, unit="pct"),
}

# Always-high categorical events
HIGH_EVENT_FIELDS = {
    "object_created",
    "corporate_action",
    "guidance",
    "acquisition",
    "earnings",
    "credit_rating",
    "rbi_policy",
    "promoter_stake",
}

HIGH_EVENT_KEYWORDS = (
    "guidance",
    "acqui",
    "merger",
    "earn",
    "result",
    "rating",
    "rbi",
    "buyback",
    "dividend",
)


@dataclass(frozen=True)
class MaterialityScore:
    field_name: str
    category: str
    magnitude: float
    score: float  # 0–100
    tier: MaterialityTier
    importance: str  # High | Medium | Low
    learn: bool
    reason: str


def score_numeric_change(
    field_name: str,
    *,
    previous: Any,
    new: Any,
    magnitude: float | None = None,
    unit_hint: str | None = None,
) -> MaterialityScore:
    """Score a numeric change against the Materiality Policy."""
    policy = DEFAULT_FIELD_POLICIES.get(field_name)
    if policy is None:
        # Unknown numeric field — medium caution, learn only if magnitude looks large
        mag = abs(float(magnitude if magnitude is not None else _delta(previous, new) or 0.0))
        tier = MaterialityTier.MEDIUM if mag >= 5 else MaterialityTier.LOW
        score = min(100.0, mag * 8.0)
        return MaterialityScore(
            field_name=field_name,
            category="General",
            magnitude=mag,
            score=round(score, 1),
            tier=tier,
            importance="Medium" if tier == MaterialityTier.MEDIUM else "Low",
            learn=tier != MaterialityTier.LOW,
            reason=f"Unscoped field {field_name} magnitude={mag}",
        )

    mag = abs(float(magnitude if magnitude is not None else _compute_magnitude(previous, new, policy.unit)))
    if mag < policy.ignore_below:
        return MaterialityScore(
            field_name=field_name,
            category=policy.category,
            magnitude=mag,
            score=round(min(100.0, (mag / max(policy.high_at, 1e-9)) * 40.0), 1),
            tier=MaterialityTier.IGNORE,
            importance="Low",
            learn=False,
            reason=f"{field_name} move {mag} below ignore threshold {policy.ignore_below}",
        )

    if mag >= policy.high_at:
        # Map magnitude onto 80–100
        score = 80.0 + min(20.0, ((mag - policy.high_at) / max(policy.high_at, 1e-9)) * 20.0)
        return MaterialityScore(
            field_name=field_name,
            category=policy.category,
            magnitude=mag,
            score=round(score, 1),
            tier=MaterialityTier.HIGH,
            importance="High",
            learn=True,
            reason=f"{field_name} material high move ({mag} {policy.unit})",
        )

    # Medium band
    span = max(policy.high_at - policy.medium_at, 1e-9)
    score = 55.0 + ((mag - policy.medium_at) / span) * 25.0
    return MaterialityScore(
        field_name=field_name,
        category=policy.category,
        magnitude=mag,
        score=round(min(79.9, score), 1),
        tier=MaterialityTier.MEDIUM,
        importance="Medium",
        learn=True,
        reason=f"{field_name} material medium move ({mag} {policy.unit})",
    )


def score_event_change(field_name: str, *, text: str | None = None) -> MaterialityScore:
    blob = f"{field_name} {text or ''}".lower()
    if field_name in HIGH_EVENT_FIELDS or any(k in blob for k in HIGH_EVENT_KEYWORDS):
        return MaterialityScore(
            field_name=field_name,
            category="Corporate",
            magnitude=1.0,
            score=92.0,
            tier=MaterialityTier.HIGH,
            importance="High",
            learn=True,
            reason=f"High-materiality institutional event: {field_name}",
        )
    return MaterialityScore(
        field_name=field_name,
        category="Corporate",
        magnitude=1.0,
        score=60.0,
        tier=MaterialityTier.MEDIUM,
        importance="Medium",
        learn=True,
        reason=f"Corporate event: {field_name}",
    )


def _delta(previous: Any, new: Any) -> float | None:
    try:
        if previous is None or new is None:
            return None
        return float(new) - float(previous)
    except (TypeError, ValueError):
        return None


def _compute_magnitude(previous: Any, new: Any, unit: str) -> float:
    try:
        p = float(previous)
        n = float(new)
    except (TypeError, ValueError):
        return 0.0
    if unit == "pct":
        if p == 0:
            return 100.0 if n != 0 else 0.0
        return abs((n - p) / p) * 100.0
    # abs and pp both use absolute difference of the provided values
    return abs(n - p)
