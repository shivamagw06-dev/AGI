"""Dynamic cash floor from E14 playbook / risk level (AM_CASH P0)."""

from __future__ import annotations

from app.contracts.engine_state import EngineState
from app.engines.e10.mapping import CASH_FLOOR, CASH_FLOOR_BY_RISK


def cash_floor_from_e14(e14: EngineState | None) -> tuple[float, str]:
    if e14 is None:
        return CASH_FLOOR["normal"], "default_normal"
    meta = e14.metadata or {}
    playbook = str(meta.get("playbook") or "normal").lower()
    risk_level = str(meta.get("risk_level") or "moderate").lower()
    gate = str(meta.get("gate") or "").lower()

    floor = CASH_FLOOR.get(playbook)
    source = f"playbook:{playbook}"
    if floor is None:
        floor = CASH_FLOOR_BY_RISK.get(risk_level, CASH_FLOOR["normal"])
        source = f"risk_level:{risk_level}"
    if gate in {"block_promotion", "research_hedge_only"}:
        floor = max(floor, CASH_FLOOR["hard_derisk"])
        source = f"gate:{gate}"
    return float(max(0.0, min(0.95, floor))), source
