"""E01 Feature Builder — Feature Registry / FeatureSnapshot → FeatureVector."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e01.mapping import (
    E01_FEATURE_IDS,
    P0_REQUIRED_FEATURES,
    REGISTRY_TO_E01,
)
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService


@dataclass
class FeatureVector:
    as_of: str
    values: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale_inputs: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    quality: dict[str, str] = field(default_factory=dict)

    def get(self, feature_id: str, default: float | None = None) -> float | None:
        if feature_id in self.values:
            return self.values[feature_id]
        return default


class E01FeatureBuilder:
    """Build E01 FeatureVector from Feature Registry only — never provider payloads."""

    def __init__(self, registry: FeatureRegistryService) -> None:
        self.registry = registry

    def build(
        self,
        *,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        prior: FeatureVector | None = None,
    ) -> FeatureVector:
        raw: dict[str, FeatureValue] = {}
        if snapshot is not None:
            for fid, fv in snapshot.values.items():
                raw[fid] = fv

        # Pull mapped registry features (PIT)
        for reg_id, e01_id in REGISTRY_TO_E01.items():
            if e01_id in raw or reg_id in raw:
                continue
            fv = self.registry.get(reg_id, symbol=None, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[reg_id] = fv

        # Also allow direct E01 feature_ids already materialized in registry
        for e01_id in E01_FEATURE_IDS:
            if e01_id in raw:
                continue
            fv = self.registry.get(e01_id, symbol=None, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[e01_id] = fv

        values: dict[str, float] = {}
        sources: dict[str, str] = {}
        quality: dict[str, str] = {}
        stale: list[str] = []

        for fid, fv in raw.items():
            e01_id = REGISTRY_TO_E01.get(fid, fid)
            if e01_id not in E01_FEATURE_IDS and e01_id not in REGISTRY_TO_E01.values():
                # Allow unknown e01 ids that appear in snapshot for extensibility
                if e01_id not in E01_FEATURE_IDS:
                    pass
            num = _to_float(fv.value)
            if num is None:
                if fv.quality_flag in ("missing", "error", "stale"):
                    stale.append(e01_id)
                continue
            values[e01_id] = _normalize_registry_units(e01_id, num)
            sources[e01_id] = fv.feature_id
            quality[e01_id] = fv.quality_flag
            if fv.quality_flag in ("stale", "partial"):
                stale.append(e01_id)

        # Derived flags / composites when inputs present (threshold feature layer, not ML)
        if "yc_slope_us" in values:
            values["yc_inversion_us"] = 1.0 if values["yc_slope_us"] < 0 else 0.0
            sources.setdefault("yc_inversion_us", "derived:yc_slope_us")

        if "usd_mom_63d" in values and "usd_strength" not in values:
            values["usd_strength"] = values["usd_mom_63d"]
            sources["usd_strength"] = "derived:usd_mom_63d"

        # Fill composites if components present and composite missing
        if "risk_appetite" not in values:
            ra = _risk_appetite(values)
            if ra is not None:
                values["risk_appetite"] = ra
                sources["risk_appetite"] = "derived:composite"
        if "stress_index" not in values:
            si = _stress_index(values)
            if si is not None:
                values["stress_index"] = si
                sources["stress_index"] = "derived:composite"
        if "growth_impulse" not in values:
            gi = _growth_impulse(values)
            if gi is not None:
                values["growth_impulse"] = gi
                sources["growth_impulse"] = "derived:composite"

        missing = [fid for fid in P0_REQUIRED_FEATURES if fid not in values]
        for fid in missing:
            if fid not in stale:
                stale.append(fid)

        # Optional prior carry for recovery detection (prior cycle state lives in service)
        _ = prior

        return FeatureVector(
            as_of=as_of,
            values=values,
            sources=sources,
            stale_inputs=sorted(set(stale)),
            missing=missing,
            quality=quality,
        )


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_registry_units(e01_id: str, value: float) -> float:
    """Align Feature Registry units to E01 formulas where needed."""
    # MACRO_OIL_MOMENTUM / DOLLAR_STRENGTH may be percent points → fraction for mom_* 
    if e01_id in ("oil_mom_63d", "usd_mom_63d", "gold_mom_63d", "copper_mom_63d"):
        if abs(value) > 1.5:
            return value / 100.0
    return value


def _risk_appetite(values: dict[str, float]) -> float | None:
    # Spec: −z(vix) −z(hy) −z(usd_mom) +z(copper_mom) — use raw proxies when z absent
    parts: list[float] = []
    if "vix_pctile_5y" in values:
        parts.append(-(values["vix_pctile_5y"] - 0.5) * 2)
    if "hy_oas" in values:
        # treat hy_oas as z if |x|<5 else scale
        hy = values["hy_oas"]
        parts.append(-(hy if abs(hy) <= 5 else hy / 100.0))
    if "usd_mom_63d" in values:
        parts.append(-values["usd_mom_63d"] * 5)
    if "copper_mom_63d" in values:
        parts.append(values["copper_mom_63d"] * 5)
    if not parts:
        return None
    return max(-3.0, min(3.0, sum(parts) / len(parts)))


def _stress_index(values: dict[str, float]) -> float | None:
    # w1·vix_pctile + w2·credit_z + w3·curve_stress
    if "vix_pctile_5y" not in values:
        return None
    vix = values["vix_pctile_5y"]
    credit = 0.0
    if "credit_stress" in values:
        credit = max(0.0, min(1.0, (values["credit_stress"] + 3) / 6))
    elif "hy_oas" in values:
        hy = values["hy_oas"]
        credit = max(0.0, min(1.0, (hy if abs(hy) <= 5 else hy / 500.0)))
    curve = 0.0
    if "yc_slope_us" in values and values["yc_slope_us"] < 0:
        curve = min(1.0, abs(values["yc_slope_us"]))
    return max(0.0, min(1.0, 0.5 * vix + 0.3 * credit + 0.2 * curve))


def _growth_impulse(values: dict[str, float]) -> float | None:
    parts: list[float] = []
    if "pmi_us" in values:
        parts.append((values["pmi_us"] - 50.0) / 5.0)
    if "pmi_in" in values:
        parts.append((values["pmi_in"] - 50.0) / 5.0)
    if "copper_mom_63d" in values:
        parts.append(values["copper_mom_63d"] * 5)
    if not parts:
        return None
    return max(-3.0, min(3.0, sum(parts) / len(parts)))
