"""L4-003 Conflict Resolver — rule-based authority ladder (E14 → E01 → E03)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.l4.collector import CollectedInputs, e01_signed, e03_signed, e14_signed


@dataclass(frozen=True)
class ConflictResolution:
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolution: str = "none"  # haircut|override|block|prefer_neutral|none
    confidence_mult: float = 1.0
    prefer_neutral: bool = False
    notes: list[str] = field(default_factory=list)
    hierarchy_trace: list[str] = field(default_factory=list)


def resolve_conflicts(inputs: CollectedInputs, evidence: dict[str, list[dict[str, Any]]]) -> ConflictResolution:
    conflicts = list(evidence.get("contradictions") or [])
    mult = 1.0
    prefer_neutral = False
    resolution = "none"
    notes: list[str] = []
    trace: list[str] = []

    e14 = inputs.e14
    e01 = inputs.e01
    e3 = e03_signed(inputs.e03)
    e1 = e01_signed(e01)
    e14s = e14_signed(e14)

    # P0 — E14 authority
    if e14 is not None:
        meta = e14.metadata or {}
        playbook = str(meta.get("playbook") or "")
        gate = str(meta.get("gate") or "")
        risk_level = str(meta.get("risk_level") or "")
        adj = float(meta.get("confidence_adjustment") or 1.0)
        trace.append(f"E14 playbook={playbook} gate={gate} risk={risk_level}")
        if playbook == "hard_derisk" or gate in {"block_promotion", "research_hedge_only"}:
            mult = min(mult, min(0.55, adj))
            prefer_neutral = True
            resolution = "block" if gate == "block_promotion" else "override"
            notes.append("E14 hard authority: prefer_neutral + confidence haircut")
        elif risk_level in {"elevated", "severe", "critical"}:
            mult = min(mult, min(0.70, adj))
            if e3 > 0.2:
                prefer_neutral = True
                resolution = "haircut"
                notes.append("E14 elevated with bullish E03 → haircut + prefer_neutral")
        else:
            mult = min(mult, adj)

    # P1 — E01 crisis / risk-off
    if e01 is not None:
        regime = str((e01.metadata or {}).get("primary_regime") or "")
        trace.append(f"E01 regime={regime}")
        if e1 < -0.35:
            mult = min(mult, 0.75)
            if e3 > 0.25:
                prefer_neutral = True
                if resolution == "none":
                    resolution = "prefer_neutral"
                notes.append("E01 risk-off vs bullish E03 → prefer_neutral")

    # Strong both-sides contradiction mass
    if conflicts and abs(e3) > 0.25 and (e14s < -0.35 or e1 < -0.35):
        mult = min(mult, 0.65)
        prefer_neutral = True
        if resolution == "none":
            resolution = "prefer_neutral"
        notes.append("Strong directional contradiction after hierarchy")

    # Completeness haircut
    if inputs.completeness < 0.5:
        mult = min(mult, 0.70)
        notes.append("Incomplete voters")
        for m in inputs.missing:
            trace.append(f"missing:{m}")

    mult = float(max(0.05, min(1.0, mult)))
    return ConflictResolution(
        conflicts=conflicts,
        resolution=resolution,
        confidence_mult=mult,
        prefer_neutral=prefer_neutral,
        notes=notes,
        hierarchy_trace=trace,
    )
