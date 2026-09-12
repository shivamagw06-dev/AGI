"""E09-001 Trend Feature Builder — FeatureSnapshot/Registry → CTA trend panels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e09.mapping import METRIC_KEYS, PANEL_ALIASES, REGISTRY_TO_METRIC
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService


@dataclass
class TrendPanel:
    symbol: str
    as_of: str
    sector_id: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class TrendFeatureBuilder:
    """Build PIT trend panels from TECH_*/VOL_*. Never MarketDataClient."""

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
    ) -> TrendPanel:
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
            metric = REGISTRY_TO_METRIC.get(fid)
            if metric is None:
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
                key = PANEL_ALIASES.get(k, k)
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

        core = ("ret_short", "ret_medium", "ret_long", "realized_vol_20")
        missing = [m for m in core if m not in metrics]
        kept = {k: v for k, v in metrics.items() if k in METRIC_KEYS}
        return TrendPanel(
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
    ) -> dict[str, TrendPanel]:
        out: dict[str, TrendPanel] = {}
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
    # Horizon returns from ROC / EMA slope when panel returns absent
    if "ret_short" not in metrics and "roc_10" in metrics:
        metrics["ret_short"] = metrics["roc_10"] / 100.0
        sources["ret_short"] = "derived:roc_10"
        stale.append("ret_short")
    if "ret_medium" not in metrics and "ema_12" in metrics and "ema_26" in metrics:
        base = abs(metrics["ema_26"]) if abs(metrics["ema_26"]) > 1e-9 else 1.0
        metrics["ret_medium"] = (metrics["ema_12"] - metrics["ema_26"]) / base
        sources["ret_medium"] = "derived:ema_spread"
        stale.append("ret_medium")
    if "ret_long" not in metrics and "ret_medium" in metrics:
        metrics["ret_long"] = metrics["ret_medium"] * 1.5
        sources["ret_long"] = "derived:ret_medium"
        stale.append("ret_long")
    if "realized_vol_20" not in metrics:
        metrics["realized_vol_20"] = 0.20
        sources["realized_vol_20"] = "default:vol"
        stale.append("realized_vol_20")

    # Time-series momentum: weighted multi-horizon sign-consistent return
    rs = metrics.get("ret_short", 0.0)
    rm = metrics.get("ret_medium", 0.0)
    rl = metrics.get("ret_long", 0.0)
    metrics["ts_momentum"] = round(0.20 * rs + 0.35 * rm + 0.45 * rl, 8)
    sources["ts_momentum"] = "derived:horizons"

    vol = max(metrics["realized_vol_20"], 0.05)
    metrics["vol_scaled_signal"] = round(metrics["ts_momentum"] / vol, 8)
    sources["vol_scaled_signal"] = "derived:ts_mom_vol"

    # Persistence: agreement of horizon signs (+ ADX strength when present)
    signs = [_sign(rs), _sign(rm), _sign(rl)]
    agree = abs(sum(signs)) / 3.0
    adx = metrics.get("adx_14")
    adx_term = min(1.0, max(0.0, (adx or 20.0) / 50.0))
    metrics["persistence"] = round(0.70 * agree + 0.30 * adx_term, 6)
    sources["persistence"] = "derived:sign_adx"

    # Exhaustion: stretched RSI / extreme short vs long divergence
    rsi = metrics.get("rsi_14", 50.0)
    rsi_ex = max(0.0, (rsi - 70.0) / 30.0) if rsi >= 50 else max(0.0, (30.0 - rsi) / 30.0)
    diverge = abs(rs - rl)
    metrics["exhaustion"] = round(min(1.0, 0.6 * rsi_ex + 0.4 * min(1.0, diverge * 5.0)), 6)
    sources["exhaustion"] = "derived:rsi_diverge"


def _sign(x: float) -> float:
    if x > 1e-9:
        return 1.0
    if x < -1e-9:
        return -1.0
    return 0.0


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
