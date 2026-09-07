"""E03-001 Technical Feature Adapter.

Maps FeatureSnapshot / registry / panel inputs → production indicator dict.
Never consumes MarketDataClient or provider payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e03.features.production_parity import calculate_indicators, frame_from_bars
from app.engines.e03.mapping import INDICATOR_KEYS
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService

# Feature Registry → indicator field (when materialised as scalar features)
REGISTRY_TO_INDICATOR: dict[str, str] = {
    "TECH_RSI_14": "rsi",
    "TECH_ROC_10": "roc_10",
}


@dataclass
class TechnicalPanel:
    symbol: str
    as_of: str
    indicators: dict[str, Any]
    stale_inputs: list[str] = field(default_factory=list)
    source: str = "panel"


class TechnicalFeatureAdapter:
    """Build production-shaped indicator dicts from institutional inputs only."""

    def __init__(self, registry: FeatureRegistryService | None = None) -> None:
        self.registry = registry

    def build(
        self,
        *,
        symbol: str,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        panel: dict[str, Any] | None = None,
    ) -> TechnicalPanel | None:
        sym = symbol.upper()
        stale: list[str] = []

        # 1) Explicit production indicator panel (golden / ORCH materialised)
        if panel and _looks_like_indicators(panel):
            return TechnicalPanel(
                symbol=sym,
                as_of=as_of,
                indicators=_coerce_indicators(panel),
                stale_inputs=stale,
                source="indicator_panel",
            )

        # 2) FeatureSnapshot metadata.agi_tech_indicators
        if snapshot is not None:
            meta_ind = _snapshot_indicators(snapshot)
            if meta_ind is not None:
                return TechnicalPanel(
                    symbol=sym,
                    as_of=as_of,
                    indicators=_coerce_indicators(meta_ind),
                    stale_inputs=stale,
                    source="snapshot_indicators",
                )
            bars = _snapshot_bars(snapshot)
            if bars is not None:
                frame = frame_from_bars(bars)
                computed = calculate_indicators(frame)
                if computed is None:
                    stale.append("insufficient_history")
                    return None
                return TechnicalPanel(
                    symbol=sym,
                    as_of=as_of,
                    indicators=computed,
                    stale_inputs=stale,
                    source="snapshot_ohlcv",
                )
            assembled = _assemble_from_feature_values(snapshot.values)
            if assembled is not None:
                return TechnicalPanel(
                    symbol=sym,
                    as_of=as_of,
                    indicators=assembled,
                    stale_inputs=stale,
                    source="snapshot_features",
                )

        # 3) Registry scalar TECH_ features + optional panel overrides
        if self.registry is not None:
            assembled = _assemble_from_registry(self.registry, sym, as_of, panel or {})
            if assembled is not None:
                return TechnicalPanel(
                    symbol=sym,
                    as_of=as_of,
                    indicators=assembled,
                    stale_inputs=stale,
                    source="registry",
                )

        return None

    def build_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
    ) -> dict[str, TechnicalPanel]:
        out: dict[str, TechnicalPanel] = {}
        symbols: set[str] = set()
        if panels:
            symbols.update(s.upper() for s in panels)
        if snapshots:
            symbols.update(s.upper() for s in snapshots)
        for sym in sorted(symbols):
            panel = (panels or {}).get(sym) or (panels or {}).get(sym.lower())
            snap = (snapshots or {}).get(sym) or (snapshots or {}).get(sym.lower())
            built = self.build(symbol=sym, as_of=as_of, snapshot=snap, panel=panel)
            if built is not None:
                out[sym] = built
        return out


def _looks_like_indicators(panel: dict[str, Any]) -> bool:
    required = {"rsi", "macd_histogram", "macd_positive", "above_sma20", "change_20d", "roc_10"}
    return required.issubset(set(panel.keys()))


def _coerce_indicators(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in INDICATOR_KEYS:
        if key not in raw:
            raise KeyError(f"missing indicator field: {key}")
        val = raw[key]
        if key in {
            "macd_positive",
            "above_sma20",
            "above_sma50",
            "above_sma200",
            "sma20_above_sma50",
        }:
            out[key] = bool(val)
        else:
            out[key] = float(val)
    return out


def _snapshot_indicators(snapshot: FeatureSnapshot) -> dict[str, Any] | None:
    # Prefer dedicated feature value metadata
    for fv in snapshot.values.values():
        if isinstance(fv.metadata, dict) and "agi_tech_indicators" in fv.metadata:
            ind = fv.metadata["agi_tech_indicators"]
            if isinstance(ind, dict) and _looks_like_indicators(ind):
                return ind
    # Or a synthetic feature carrying the dict in metadata only
    return None


def _snapshot_bars(snapshot: FeatureSnapshot) -> list[dict[str, Any]] | None:
    for fv in snapshot.values.values():
        bars = fv.metadata.get("ohlcv_bars") if isinstance(fv.metadata, dict) else None
        if isinstance(bars, list) and len(bars) >= MIN_BARS_SAFE:
            return bars
    return None


MIN_BARS_SAFE = 200


def _assemble_from_feature_values(values: dict[str, FeatureValue]) -> dict[str, Any] | None:
    """Assemble when snapshot carries a TECH_INDICATORS bundle feature."""
    bundle = values.get("TECH_AGI_INDICATORS")
    if bundle is None:
        return None
    meta = bundle.metadata or {}
    ind = meta.get("indicators")
    if isinstance(ind, dict) and _looks_like_indicators(ind):
        return _coerce_indicators(ind)
    return None


def _assemble_from_registry(
    registry: FeatureRegistryService,
    symbol: str,
    as_of: str,
    panel: dict[str, Any],
) -> dict[str, Any] | None:
    if _looks_like_indicators(panel):
        return _coerce_indicators(panel)
    # Partial registry fill is insufficient for production parity — require full panel
    return None
