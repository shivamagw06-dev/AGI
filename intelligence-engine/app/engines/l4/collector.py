"""L4-001 EngineState Collector — E01/E14/E02/E03 + optional soft E11."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e02.exposure import E02Exposure
from app.engines.e03.alpha import E03Alpha
from app.engines.e11.sentiment_state import E11State


@dataclass
class CollectedInputs:
    symbol: str
    as_of: str
    e01: EngineState | None = None
    e14: EngineState | None = None
    e02: E02Exposure | None = None
    e03: E03Alpha | None = None
    e11: E11State | None = None
    missing: list[str] = field(default_factory=list)
    upstream_hashes: dict[str, str] = field(default_factory=dict)

    @property
    def completeness(self) -> float:
        # Core voters only for completeness; E11 soft optional
        present = sum(
            1
            for x in (self.e01, self.e14, self.e02, self.e03)
            if x is not None
        )
        return present / 4.0


def collect_inputs(
    *,
    symbol: str,
    as_of: str,
    e01: EngineState | None,
    e14: EngineState | None,
    e02: E02Exposure | None,
    e03: E03Alpha | None,
    e11: E11State | None = None,
) -> CollectedInputs:
    """Assemble typed upstream products. No FeatureSnapshot / MarketData."""
    missing: list[str] = []
    hashes: dict[str, str] = {}
    if e01 is None:
        missing.append("E01State")
    else:
        hashes["E01"] = e01.hash
    if e14 is None:
        missing.append("E14State")
    else:
        hashes["E14"] = e14.hash
    if e02 is None:
        missing.append("E02Exposure")
    else:
        hashes["E02"] = e02.hash
    if e03 is None:
        missing.append("E03Alpha")
    else:
        hashes["E03"] = e03.hash
    # E11 soft: absence is not a hard missing dependency (chaos: weight 0)
    if e11 is not None:
        hashes["E11"] = e11.hash
    return CollectedInputs(
        symbol=symbol.upper(),
        as_of=as_of,
        e01=e01,
        e14=e14,
        e02=e02,
        e03=e03,
        e11=e11,
        missing=missing,
        upstream_hashes=hashes,
    )


def e01_signed(state: EngineState | None) -> float:
    """Map E01 regime/score to bullish-relative signed [-1, 1]."""
    if state is None:
        return 0.0
    meta = state.metadata or {}
    regime = str(meta.get("primary_regime") or "").lower()
    if "crisis" in regime or "risk_off" in regime or "contraction" in regime:
        base = -0.55
    elif "expansion" in regime or "risk_on" in regime:
        base = 0.45
    elif "transition" in regime:
        base = 0.0
    else:
        score = float(state.score.normalized_0_100)
        base = max(-1.0, min(1.0, (score - 50.0) / 50.0))
    return float(max(-1.0, min(1.0, base)))


def e14_signed(state: EngineState | None) -> float:
    """High risk → bearish-relative signed (defensive)."""
    if state is None:
        return 0.0
    meta = state.metadata or {}
    playbook = str(meta.get("playbook") or "").lower()
    risk_level = str(meta.get("risk_level") or "").lower()
    score = float(state.score.normalized_0_100)
    # Invert: higher risk score → more negative
    signed = -max(-1.0, min(1.0, (score - 50.0) / 50.0))
    if playbook == "hard_derisk" or risk_level in {"severe", "critical"}:
        signed = min(signed, -0.70)
    elif risk_level == "elevated":
        signed = min(signed, -0.35)
    return float(signed)


def e03_signed(alpha: E03Alpha | None) -> float:
    if alpha is None:
        return 0.0
    return float(max(-1.0, min(1.0, (alpha.agi_tech_score - 50.0) / 50.0)))


def e02_context(exposure: E02Exposure | None) -> dict[str, Any]:
    if exposure is None:
        return {}
    return {
        "dominant_factor": exposure.dominant_factor,
        "composite_score": exposure.composite_score,
        "sector_id": exposure.sector_id,
        "style_box": exposure.style_box,
    }
