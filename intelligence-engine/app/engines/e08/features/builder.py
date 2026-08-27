"""E08-001 Volatility Feature Builder — FeatureSnapshot/Registry → VOL panels."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.engines.e08.mapping import METRIC_KEYS, REGISTRY_TO_METRIC
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService


@dataclass
class VolatilityPanel:
    symbol: str
    as_of: str
    sector_id: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class VolatilityFeatureBuilder:
    """Build PIT volatility panels. Never MarketDataClient / provider payloads."""

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
    ) -> VolatilityPanel:
        raw: dict[str, FeatureValue] = {}
        if snapshot is not None:
            raw.update(snapshot.values)

        for reg_id in REGISTRY_TO_METRIC:
            if reg_id in raw:
                continue
            fv = self.registry.get(reg_id, symbol=symbol, as_of=as_of, pit_mode=True)
            if fv is None:
                fv = self.registry.get(reg_id, symbol=None, as_of=as_of, pit_mode=True)
            if fv is not None:
                raw[reg_id] = fv

        metrics: dict[str, float] = {}
        sources: dict[str, str] = {}
        stale: list[str] = []

        for fid, fv in raw.items():
            metric = REGISTRY_TO_METRIC.get(fid, fid)
            if metric not in METRIC_KEYS and metric not in REGISTRY_TO_METRIC.values():
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
                if k == "sector_id":
                    continue
                num = _to_float(v)
                if num is None:
                    continue
                # Accept golden aliases
                key = {
                    "sigma_60": "hist_vol_60",
                    "rv_20": "realized_vol_20",
                    "realized_vol": "realized_vol_20",
                    "hist_vol": "hist_vol_60",
                }.get(k, k)
                if key not in METRIC_KEYS and key not in ("hist_vol_60", "realized_vol_20", "atr_14", "iv_rank", "expected_move"):
                    if key in ("beta",):
                        continue
                    # ignore non-vol panel noise from shared e02 panels
                    if key not in METRIC_KEYS:
                        continue
                metrics[key] = num
                sources.setdefault(key, "panel_override")

        _derive_missing(metrics, sources, stale)

        sec = sector_id
        if sec is None and snapshot is not None:
            for fv in snapshot.values.values():
                sid = (fv.metadata or {}).get("sector_id")
                if sid:
                    sec = str(sid)
                    break

        core = ("realized_vol_20", "hist_vol_60")
        missing = [m for m in core if m not in metrics]
        kept = {k: v for k, v in metrics.items() if k in METRIC_KEYS}
        return VolatilityPanel(
            symbol=symbol.upper(),
            as_of=as_of,
            sector_id=sec,
            metrics=kept,
            sources={k: sources[k] for k in kept if k in sources},
            stale=sorted(set(stale)),
            missing=missing,
        )

    def build_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
    ) -> dict[str, VolatilityPanel]:
        out: dict[str, VolatilityPanel] = {}
        symbols: set[str] = set()
        if panels:
            symbols |= set(panels.keys())
        if snapshots:
            symbols |= set(snapshots.keys())
        for sym in sorted(symbols):
            meta = (panels or {}).get(sym) or (panels or {}).get(sym.upper()) or {}
            out[sym.upper()] = self.build_panel(
                symbol=sym,
                as_of=as_of,
                snapshot=(snapshots or {}).get(sym) or (snapshots or {}).get(sym.upper()),
                sector_id=meta.get("sector_id"),
                metrics_override={k: v for k, v in meta.items() if k != "sector_id"},
            )
        return out


def _derive_missing(
    metrics: dict[str, float],
    sources: dict[str, str],
    stale: list[str],
) -> None:
    if "hist_vol_60" not in metrics and "realized_vol_20" in metrics:
        metrics["hist_vol_60"] = metrics["realized_vol_20"] * 1.05
        sources["hist_vol_60"] = "derived:realized_vol_20"
        stale.append("hist_vol_60")
    if "realized_vol_20" not in metrics and "hist_vol_60" in metrics:
        metrics["realized_vol_20"] = metrics["hist_vol_60"] * 0.95
        sources["realized_vol_20"] = "derived:hist_vol_60"
        stale.append("realized_vol_20")
    if "vol_ratio" not in metrics and "realized_vol_20" in metrics and "hist_vol_60" in metrics:
        hv = max(metrics["hist_vol_60"], 1e-6)
        metrics["vol_ratio"] = metrics["realized_vol_20"] / hv
        sources["vol_ratio"] = "derived:rv_hv"
    if "expansion_score" not in metrics and "vol_ratio" in metrics:
        # >1 ⇒ expansion; map to 0–100
        r = metrics["vol_ratio"]
        metrics["expansion_score"] = round(max(0.0, min(100.0, (r - 1.0) * 100.0 + 50.0)), 6)
        sources["expansion_score"] = "derived:vol_ratio"
    if "compression_score" not in metrics and "vol_ratio" in metrics:
        r = metrics["vol_ratio"]
        metrics["compression_score"] = round(max(0.0, min(100.0, (1.0 - r) * 100.0 + 50.0)), 6)
        sources["compression_score"] = "derived:vol_ratio"
    # Basic expected move when IV rank available (no options pricing model)
    if "expected_move" not in metrics and "iv_rank" in metrics and "realized_vol_20" in metrics:
        # IV rank in [0,100] scales short-horizon move proxy from realized vol
        iv = max(0.0, min(100.0, metrics["iv_rank"])) / 100.0
        metrics["expected_move"] = round(metrics["realized_vol_20"] * math.sqrt(5.0 / 252.0) * (0.7 + 0.6 * iv), 8)
        sources["expected_move"] = "derived:iv_rank_rv"
    elif "expected_move" not in metrics and "realized_vol_20" in metrics:
        metrics["expected_move"] = round(metrics["realized_vol_20"] * math.sqrt(5.0 / 252.0), 8)
        sources["expected_move"] = "derived:rv_5d"
        stale.append("expected_move")


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
