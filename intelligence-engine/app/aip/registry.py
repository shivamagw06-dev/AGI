"""AIP-02 Dynamic Weight Registry — shadow weight sets only; never mutates L4 production."""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime, timezone

from app.aip.models import WeightSet
from app.engines.l4.mapping import VOTER_WEIGHTS, WEIGHT_SET_ID


def _iso(ts: datetime | None = None) -> str:
    t = ts or datetime.now(timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def baseline_weight_set() -> WeightSet:
    """Current frozen L4 P0 shadow voters — read-only baseline."""
    return WeightSet(
        weight_set_id=WEIGHT_SET_ID,
        name="L4 P0 Shadow Voters (baseline)",
        description="Frozen Architecture v1.0.1 L4 shadow voter weights. Production mutation forbidden.",
        weights={k: float(v) for k, v in VOTER_WEIGHTS.items()},
        baseline=True,
        shadow_only=True,
        production=False,
        created_at="2026-01-01T00:00:00Z",
        notes=[
            "Source: app.engines.l4.mapping.VOTER_WEIGHTS",
            "L4 remains shadow",
            "AIP never writes back to mapping.py",
        ],
    )


# Seed regime / sector candidates for AIP-04 experiments (shadow registry only).
_SEED_CANDIDATES: list[WeightSet] = [
    WeightSet(
        weight_set_id="aip_regime_risk_on_v1",
        name="Regime Risk-On tilt",
        description="Slightly higher E01/E03 when risk-on; shadow candidate.",
        weights={"E03": 0.65, "E01": 0.25, "E14": 0.08, "E11": 0.05, "E02": 0.00},
        regime="RiskOn",
        parent_weight_set_id=WEIGHT_SET_ID,
        created_at="2026-01-01T00:00:00Z",
        notes=["Shadow only", "AIP-04"],
    ),
    WeightSet(
        weight_set_id="aip_regime_risk_off_v1",
        name="Regime Risk-Off tilt",
        description="Higher E14 risk weight when risk-off; shadow candidate.",
        weights={"E03": 0.55, "E01": 0.15, "E14": 0.25, "E11": 0.05, "E02": 0.00},
        regime="RiskOff",
        parent_weight_set_id=WEIGHT_SET_ID,
        created_at="2026-01-01T00:00:00Z",
        notes=["Shadow only", "AIP-04"],
    ),
    WeightSet(
        weight_set_id="aip_sector_financials_v1",
        name="Sector Financials tilt",
        description="Sector-conditioned shadow weights for financials.",
        weights={"E03": 0.60, "E01": 0.20, "E14": 0.15, "E11": 0.05, "E02": 0.00},
        sector="Financials",
        parent_weight_set_id=WEIGHT_SET_ID,
        created_at="2026-01-01T00:00:00Z",
        notes=["Shadow only", "AIP-04 sector"],
    ),
    WeightSet(
        weight_set_id="aip_e03_heavier_v1",
        name="E03 heavier shadow",
        description="Hypothesis: larger E03 L4 weight improves IC without worse drawdown.",
        weights={"E03": 0.80, "E01": 0.12, "E14": 0.06, "E11": 0.02, "E02": 0.00},
        parent_weight_set_id=WEIGHT_SET_ID,
        created_at="2026-01-01T00:00:00Z",
        notes=["Shadow only", "AIP-02/AIP-03"],
    ),
]


class DynamicWeightRegistry:
    """In-memory shadow registry. Cannot mark weight sets as production."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        base = baseline_weight_set()
        self._sets: dict[str, WeightSet] = {base.weight_set_id: base}
        for ws in _SEED_CANDIDATES:
            self._sets[ws.weight_set_id] = ws

    def list(self) -> list[WeightSet]:
        with self._lock:
            return [deepcopy(v) for v in self._sets.values()]

    def get(self, weight_set_id: str) -> WeightSet | None:
        with self._lock:
            ws = self._sets.get(weight_set_id)
            return deepcopy(ws) if ws else None

    def baseline(self) -> WeightSet:
        with self._lock:
            return deepcopy(self._sets[WEIGHT_SET_ID])

    def register(
        self,
        *,
        weight_set_id: str,
        name: str,
        weights: dict[str, float],
        description: str = "",
        regime: str | None = None,
        sector: str | None = None,
        notes: list[str] | None = None,
    ) -> WeightSet:
        if weight_set_id == WEIGHT_SET_ID:
            raise ValueError("Cannot overwrite frozen L4 baseline weight set")
        cleaned = {str(k).upper(): float(v) for k, v in weights.items()}
        for eng in ("E03", "E01", "E14", "E11", "E02"):
            cleaned.setdefault(eng, 0.0)
        if any(v < 0 for v in cleaned.values()):
            raise ValueError("Weights must be non-negative")
        ws = WeightSet(
            weight_set_id=weight_set_id,
            name=name,
            description=description,
            weights=cleaned,
            regime=regime,
            sector=sector,
            baseline=False,
            shadow_only=True,
            production=False,
            parent_weight_set_id=WEIGHT_SET_ID,
            created_at=_iso(),
            notes=(notes or []) + ["Shadow only", "Never applied to production L4"],
        )
        with self._lock:
            self._sets[weight_set_id] = ws
            return deepcopy(ws)
