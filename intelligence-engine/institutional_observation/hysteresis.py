"""Hysteresis thresholds — prevent alert fatigue and unnecessary recomputation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class HysteresisProfile:
    """Configurable materiality gates for observation + decision re-evaluation."""

    # Silent graph updates below these thresholds
    valuation_change_pct_min: float = 2.0
    confidence_change_min: int = 1
    forecast_revision_min: float = 0.05
    business_quality_change_min: float = 2.0
    # Always create observations at/above this severity
    force_observe_severities: tuple[str, ...] = ("critical", "high")
    # Decision recompute requires at least this severity OR recommendation change risk
    recompute_min_severity: str = "high"
    # Ignore noise
    ignore_severity: str = "ignore"
    profile_id: str = "default"
    profile_version: str = "io-01-hysteresis-v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_HYSTERESIS = HysteresisProfile()

_SEVERITY_RANK = {"ignore": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get(str(severity or "").strip().lower(), 0)


def meets_recompute_threshold(severity: str, profile: HysteresisProfile | None = None) -> bool:
    profile = profile or DEFAULT_HYSTERESIS
    return severity_rank(severity) >= severity_rank(profile.recompute_min_severity)


def should_emit_observation(
    severity: str,
    *,
    profile: HysteresisProfile | None = None,
    forced: bool = False,
) -> bool:
    profile = profile or DEFAULT_HYSTERESIS
    sev = str(severity or "").strip().lower()
    if forced:
        return True
    if sev == profile.ignore_severity or sev == "ignore":
        return False
    if sev in {s.lower() for s in profile.force_observe_severities}:
        return True
    return severity_rank(sev) >= severity_rank("medium")
