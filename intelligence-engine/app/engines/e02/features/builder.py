"""E02 Factor Feature Builder — FeatureSnapshot/Registry → symbol metric panels."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.engines.e02.mapping import METRIC_KEYS, REGISTRY_TO_METRIC
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService


@dataclass
class SymbolPanel:
    symbol: str
    as_of: str
    sector_id: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    # Intermediate FACTOR_* raw composites before cross-section (optional audit)
    factor_raw: dict[str, float] = field(default_factory=dict)


class FactorFeatureBuilder:
    """Build PIT metric panels. Never MarketDataClient / provider payloads."""

    def __init__(self, registry: FeatureRegistryService) -> None:
        self.registry = registry

    def build_panel(
        self,
        *,
        symbol: str,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        sector_id: str | None = None,
        metrics_override: dict[str, float] | None = None,
    ) -> SymbolPanel:
        raw: dict[str, FeatureValue] = {}
        if snapshot is not None:
            raw.update(snapshot.values)

        for reg_id, metric in REGISTRY_TO_METRIC.items():
            if metric in raw or reg_id in raw:
                continue
            fv = self.registry.get(reg_id, symbol=symbol, as_of=as_of, pit_mode=True)
            if fv is None:
                fv = self.registry.get(reg_id, symbol=None, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[reg_id] = fv

        # Direct metric feature_ids
        for metric in METRIC_KEYS:
            if metric in raw:
                continue
            fv = self.registry.get(metric, symbol=symbol, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[metric] = fv

        metrics: dict[str, float] = {}
        sources: dict[str, str] = {}
        stale: list[str] = []

        for fid, fv in raw.items():
            metric = REGISTRY_TO_METRIC.get(fid, fid)
            if metric not in METRIC_KEYS and metric not in REGISTRY_TO_METRIC.values():
                # Allow FACTOR_* passthrough later; skip unknown for metrics
                if metric.startswith("FACTOR_"):
                    continue
            num = _to_float(fv.value)
            if num is None:
                if fv.quality_flag in ("missing", "error", "stale"):
                    stale.append(metric)
                continue
            metrics[metric] = num
            sources[metric] = fv.feature_id
            if fv.quality_flag in ("stale", "partial"):
                stale.append(metric)

        if metrics_override:
            for k, v in metrics_override.items():
                num = _to_float(v)
                if num is None:
                    continue
                metrics[k] = num
                sources.setdefault(k, "panel_override")

        # Derived metrics
        if "log_mcap" not in metrics and "mcap" in metrics and metrics["mcap"] > 0:
            metrics["log_mcap"] = math.log(metrics["mcap"])
            sources["log_mcap"] = "derived:mcap"
        if "sigma_60" not in metrics and "rv_20" in metrics:
            metrics["sigma_60"] = metrics["rv_20"]
            sources["sigma_60"] = "derived:rv_20"
        if "beta" not in metrics and "sigma_60" in metrics:
            # Conservative proxy — not a live beta estimate from market data
            metrics["beta"] = max(0.2, min(2.0, metrics["sigma_60"] / 0.20))
            sources["beta"] = "derived:sigma_proxy"
            stale.append("beta")

        # Momentum from closes embedded in snapshot metadata/context values
        if snapshot is not None and snapshot.values:
            closes = _extract_closes(snapshot)
            if closes:
                _fill_momentum(metrics, sources, closes)

        sec = sector_id
        if sec is None and snapshot is not None:
            # sector may ride on any value metadata
            for fv in snapshot.values.values():
                sid = (fv.metadata or {}).get("sector_id")
                if sid:
                    sec = str(sid)
                    break

        missing = [m for m in ("ret_12_1", "roe", "ep_ttm", "log_mcap", "adv_value_20d") if m not in metrics]
        return SymbolPanel(
            symbol=symbol.upper(),
            as_of=as_of,
            sector_id=sec,
            metrics=metrics,
            sources=sources,
            stale=sorted(set(stale)),
            missing=missing,
        )

    def build_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
    ) -> dict[str, SymbolPanel]:
        out: dict[str, SymbolPanel] = {}
        symbols = set()
        if panels:
            symbols |= set(panels.keys())
        if snapshots:
            symbols |= set(snapshots.keys())
        for sym in sorted(symbols):
            meta = (panels or {}).get(sym) or {}
            out[sym.upper()] = self.build_panel(
                symbol=sym,
                as_of=as_of,
                snapshot=(snapshots or {}).get(sym) or (snapshots or {}).get(sym.upper()),
                sector_id=meta.get("sector_id"),
                metrics_override={k: v for k, v in meta.items() if k != "sector_id"},
            )
        return out


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_closes(snapshot: FeatureSnapshot) -> list[float]:
    for fv in snapshot.values.values():
        bars = (fv.metadata or {}).get("closes") or (fv.metadata or {}).get("bars")
        if isinstance(bars, list) and bars:
            if isinstance(bars[0], (int, float)):
                return [float(x) for x in bars]
            if isinstance(bars[0], dict) and "close" in bars[0]:
                return [float(b["close"]) for b in bars]
    return []


def _fill_momentum(metrics: dict[str, float], sources: dict[str, str], closes: list[float]) -> None:
    n = len(closes)
    if n >= 252 and "ret_12_1" not in metrics:
        # 12-1: skip last ~21 sessions
        p_lag = closes[-21]
        p_start = closes[-252]
        if p_start != 0:
            metrics["ret_12_1"] = p_lag / p_start - 1.0
            sources["ret_12_1"] = "derived:closes"
    if n >= 126 and "ret_6_1" not in metrics:
        p_lag = closes[-21] if n >= 21 else closes[-1]
        p_start = closes[-126]
        if p_start != 0:
            metrics["ret_6_1"] = p_lag / p_start - 1.0
            sources["ret_6_1"] = "derived:closes"
    if n >= 63 and "ret_3_0" not in metrics:
        p_start = closes[-63]
        if p_start != 0:
            metrics["ret_3_0"] = closes[-1] / p_start - 1.0
            sources["ret_3_0"] = "derived:closes"
