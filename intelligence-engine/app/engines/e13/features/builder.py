"""E13-001 Fundamental Feature Builder — FeatureSnapshot/Registry → PIT fund panels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e13.mapping import METRIC_KEYS, REGISTRY_TO_METRIC
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService


@dataclass
class FundamentalPanel:
    symbol: str
    as_of: str
    sector_id: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class FundamentalFeatureBuilder:
    """Build PIT fundamental panels. Never MarketDataClient / provider payloads."""

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
    ) -> FundamentalPanel:
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
            if metric not in METRIC_KEYS:
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
                metrics[k] = num
                sources.setdefault(k, "panel_override")

        _derive_missing(metrics, sources, stale)

        sec = sector_id
        if sec is None and snapshot is not None:
            for fv in snapshot.values.values():
                sid = (fv.metadata or {}).get("sector_id")
                if sid:
                    sec = str(sid)
                    break

        core = ("roe", "roic", "revenue_growth", "ep_ttm", "fcf_yield")
        missing = [m for m in core if m not in metrics]
        kept = {k: v for k, v in metrics.items() if k in METRIC_KEYS}
        return FundamentalPanel(
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
    ) -> dict[str, FundamentalPanel]:
        out: dict[str, FundamentalPanel] = {}
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
    """Fill P0 gaps from available PIT fundamentals (no market data)."""
    if "roce" not in metrics and "roic" in metrics:
        metrics["roce"] = metrics["roic"]
        sources["roce"] = "derived:roic"
    if "net_margin" not in metrics and "oper_margin" in metrics:
        metrics["net_margin"] = metrics["oper_margin"] * 0.75
        sources["net_margin"] = "derived:oper_margin"
        stale.append("net_margin")
    if "debt_equity" not in metrics and "leverage" in metrics:
        metrics["debt_equity"] = metrics["leverage"]
        sources["debt_equity"] = "derived:leverage"
    if "interest_coverage" not in metrics and "leverage" in metrics:
        metrics["interest_coverage"] = 1.0 / max(metrics["leverage"], 0.05)
        sources["interest_coverage"] = "derived:leverage_inv"
        stale.append("interest_coverage")
    if "fcf_conversion" not in metrics and "fcf_yield" in metrics and "ep_ttm" in metrics:
        metrics["fcf_conversion"] = metrics["fcf_yield"] / max(abs(metrics["ep_ttm"]), 0.01)
        sources["fcf_conversion"] = "derived:fcf_ep"
    if "revenue_growth" not in metrics and "earn_stability" in metrics:
        # Stability-scaled growth proxy when explicit growth series absent
        metrics["revenue_growth"] = metrics["earn_stability"] * 0.12
        sources["revenue_growth"] = "derived:earn_stability"
        stale.append("revenue_growth")
    if "eps_growth" not in metrics and "earn_stability" in metrics:
        roe_boost = metrics.get("roe", 0.1)
        metrics["eps_growth"] = metrics["earn_stability"] * 0.10 + max(0.0, roe_boost - 0.1) * 0.2
        sources["eps_growth"] = "derived:earn_stability_roe"
        stale.append("eps_growth")
    if "peg" not in metrics and "ep_ttm" in metrics and "eps_growth" in metrics:
        g = max(metrics["eps_growth"], 0.01)
        pe = 1.0 / max(metrics["ep_ttm"], 0.01)
        metrics["peg"] = pe / (g * 100.0) if g * 100.0 > 0 else pe
        sources["peg"] = "derived:ep_eps_growth"


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
