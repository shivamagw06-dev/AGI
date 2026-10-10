"""E14 Risk Feature Builder — Feature Registry + E01State → RiskFeatureVector."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e14.mapping import (
    E14_FEATURE_IDS,
    P0_REQUIRED_FEATURES,
    REGISTRY_TO_E14,
)
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService


@dataclass
class RiskFeatureVector:
    as_of: str
    values: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale_inputs: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    e01_present: bool = False
    e01_ref: dict[str, Any] = field(default_factory=dict)

    def get(self, feature_id: str, default: float | None = None) -> float | None:
        if feature_id in self.values:
            return self.values[feature_id]
        return default


class E14FeatureBuilder:
    """Build risk features from Feature Registry + E01State. Never MarketDataClient."""

    def __init__(self, registry: FeatureRegistryService) -> None:
        self.registry = registry

    def build(
        self,
        *,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        e01_state: EngineState | None = None,
        book: dict[str, float] | None = None,
    ) -> RiskFeatureVector:
        raw: dict[str, FeatureValue] = {}
        if snapshot is not None:
            raw.update(snapshot.values)

        for reg_id, e14_id in REGISTRY_TO_E14.items():
            if e14_id in raw or reg_id in raw:
                continue
            fv = self.registry.get(reg_id, symbol=None, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[reg_id] = fv

        for fid in E14_FEATURE_IDS:
            if fid in raw:
                continue
            fv = self.registry.get(fid, symbol=None, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[fid] = fv

        values: dict[str, float] = {}
        sources: dict[str, str] = {}
        stale: list[str] = []

        for fid, fv in raw.items():
            e14_id = REGISTRY_TO_E14.get(fid, fid)
            num = _to_float(fv.value)
            if num is None:
                if fv.quality_flag in ("missing", "error", "stale"):
                    stale.append(e14_id)
                continue
            values[e14_id] = num
            sources[e14_id] = fv.feature_id
            if fv.quality_flag in ("stale", "partial"):
                stale.append(e14_id)

        if book:
            for k, v in book.items():
                num = _to_float(v)
                if num is None:
                    continue
                values[k] = num
                sources.setdefault(k, "book_input")

        e01_present = e01_state is not None
        e01_ref: dict[str, Any] = {}
        if e01_state is not None:
            meta = e01_state.metadata or {}
            e01_ref = {
                "as_of": e01_state.as_of,
                "primary_regime": meta.get("primary_regime"),
                "risk_level": meta.get("risk_level"),
                "size_multiplier": meta.get("size_multiplier"),
                "hash": e01_state.hash,
            }
            # Spec §4 SM_MACRO_BRIDGE — E01 → macro_risk_bridge
            if "macro_risk_bridge" not in values:
                values["macro_risk_bridge"] = _macro_risk_bridge(e01_state)
                sources["macro_risk_bridge"] = "e01_bridge"
            # Vol / stress proxies from E01 axes when missing
            axes = meta.get("axes") or {}
            if "vix_pctile_5y" not in values:
                vol_state = (axes.get("R_VOL") or {}).get("state")
                values["vix_pctile_5y"] = {
                    "crisis_vol": 0.97,
                    "high_vol": 0.80,
                    "normal_vol": 0.45,
                    "low_vol": 0.20,
                }.get(vol_state, 0.50)
                sources["vix_pctile_5y"] = "e01_R_VOL"
                stale.append("vix_pctile_5y")  # bridged proxy, mark partial coverage
        else:
            # Fail-closed prior: force conservative macro bridge
            values.setdefault("macro_risk_bridge", 75.0)
            sources.setdefault("macro_risk_bridge", "e01_missing_fail_closed")
            stale.append("E01State")

        # Derived composites when partial inputs exist
        if "fragility_index" not in values:
            frag = _fragility(values)
            if frag is not None:
                values["fragility_index"] = frag
                sources["fragility_index"] = "derived:composite"
        if "tail_risk_score" not in values:
            tail = _tail(values)
            if tail is not None:
                values["tail_risk_score"] = tail
                sources["tail_risk_score"] = "derived:composite"
        if "crowding_index" not in values and "herding_agib" in values:
            values["crowding_index"] = max(0.0, min(100.0, values["herding_agib"]))
            sources["crowding_index"] = "derived:herding_agib"
        if "liquidity_index" not in values and "pct_adv_proposed" in values:
            # High %ADV → low liquidity score
            padv = values["pct_adv_proposed"]
            values["liquidity_index"] = max(0.0, min(100.0, 100.0 - padv * 30.0))
            sources["liquidity_index"] = "derived:pct_adv_proposed"
        if "gap_buffer_mult" not in values:
            values["gap_buffer_mult"] = 1.0
            sources["gap_buffer_mult"] = "default"

        missing = [fid for fid in P0_REQUIRED_FEATURES if fid not in values]
        for fid in missing:
            if fid not in stale:
                stale.append(fid)

        return RiskFeatureVector(
            as_of=as_of,
            values=values,
            sources=sources,
            stale_inputs=sorted(set(stale)),
            missing=missing,
            e01_present=e01_present,
            e01_ref=e01_ref,
        )


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _macro_risk_bridge(e01: EngineState) -> float:
    """Map E01State → macro_risk_bridge 0–100 (higher = more macro risk)."""
    meta = e01.metadata or {}
    risk_level = meta.get("risk_level") or "moderate"
    base = {
        "low": 25.0,
        "moderate": 45.0,
        "elevated": 65.0,
        "critical": 90.0,
    }.get(str(risk_level), 50.0)
    axes = meta.get("axes") or {}
    stress = (axes.get("R_STRESS") or {}).get("state")
    if stress == "crisis":
        base = max(base, 92.0)
    elif stress == "elevated_stress":
        base = max(base, 75.0)
    vol = (axes.get("R_VOL") or {}).get("state")
    if vol == "crisis_vol":
        base = max(base, 90.0)
    elif vol == "high_vol":
        base = max(base, 70.0)
    # Invert supportive macro_score slightly
    macro_score = meta.get("macro_score")
    if isinstance(macro_score, (int, float)):
        base = 0.7 * base + 0.3 * (100.0 - float(macro_score))
    return float(max(0.0, min(100.0, base)))


def _fragility(values: dict[str, float]) -> float | None:
    parts: list[float] = []
    if "corr_avg_20d" in values:
        parts.append(values["corr_avg_20d"] * 100.0)
    if "corr_spike" in values:
        parts.append(min(100.0, max(0.0, values["corr_spike"] * 200.0)))
    if "crowding_index" in values:
        parts.append(values["crowding_index"])
    if "vix_pctile_5y" in values:
        parts.append(values["vix_pctile_5y"] * 100.0)
    if not parts:
        return None
    return float(max(0.0, min(100.0, sum(parts) / len(parts))))


def _tail(values: dict[str, float]) -> float | None:
    parts: list[float] = []
    if "vix_pctile_5y" in values:
        parts.append(values["vix_pctile_5y"] * 100.0)
    if "stress_worst_pnl" in values:
        # more negative → higher tail risk
        parts.append(min(100.0, max(0.0, -values["stress_worst_pnl"] * 4.0)))
    if "expected_dd_3m_p95" in values:
        parts.append(min(100.0, values["expected_dd_3m_p95"] * 100.0 / 0.40))
    if "macro_risk_bridge" in values:
        parts.append(values["macro_risk_bridge"])
    if not parts:
        return None
    return float(max(0.0, min(100.0, sum(parts) / len(parts))))
