"""E04-001 Relative Value Feature Builder — pair panels from FeatureSnapshot / series."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e04.features.pairs import (
    canonical_pair_id,
    discover_pairs,
    extract_closes,
    synthesize_closes,
)
from app.engines.e04.mapping import DEFAULT_LOOKBACK, REGISTRY_RVAL
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService


@dataclass
class PairPanel:
    pair_id: str
    leg_a: str
    leg_b: str
    as_of: str
    sector_id: str | None = None
    closes_a: list[float] = field(default_factory=list)
    closes_b: list[float] = field(default_factory=list)
    rval_meta: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    discovery: str = "static"


class RelativeValueFeatureBuilder:
    """Build pair panels. Never MarketDataClient / provider payloads."""

    def __init__(self, registry: FeatureRegistryService) -> None:
        self.registry = registry

    def build_pairs(
        self,
        *,
        as_of: str,
        symbol_panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
        user_pairs: list[tuple[str, str]] | None = None,
        static_pairs: list[tuple[str, str]] | None = None,
        lookback: int = DEFAULT_LOOKBACK,
    ) -> dict[str, PairPanel]:
        panels = {k.upper(): dict(v) for k, v in (symbol_panels or {}).items()}
        # Merge closes from snapshots if present
        if snapshots:
            for sym, snap in snapshots.items():
                s = sym.upper()
                meta = panels.setdefault(s, {})
                closes = _closes_from_snapshot(snap)
                if closes:
                    meta["closes"] = closes
                for fv in snap.values.values():
                    sid = (fv.metadata or {}).get("sector_id")
                    if sid:
                        meta.setdefault("sector_id", str(sid))

        symbols = sorted(panels.keys())
        sectors = {s: panels[s].get("sector_id") for s in symbols}
        pairs = discover_pairs(
            symbols=symbols,
            sectors=sectors,
            user_pairs=user_pairs,
            static_pairs=static_pairs,
            index_constituents=True,
            sector_peers=True,
        )

        out: dict[str, PairPanel] = {}
        for a, b in pairs:
            pa = panels.get(a, {})
            pb = panels.get(b, {})
            ca = extract_closes(pa) or synthesize_closes(pa, n=lookback, seed=a)
            cb = extract_closes(pb) or synthesize_closes(pb, n=lookback, seed=b)
            # Align length
            n = min(len(ca), len(cb), lookback)
            ca, cb = ca[-n:], cb[-n:]
            stale: list[str] = []
            sources = {"closes_a": "panel_or_synthetic", "closes_b": "panel_or_synthetic"}
            if extract_closes(pa) is None:
                stale.append("closes_a")
            if extract_closes(pb) is None:
                stale.append("closes_b")

            rval_meta = _rval_from_registry(self.registry, a, b, as_of)
            sec = pa.get("sector_id") if pa.get("sector_id") == pb.get("sector_id") else None
            pid = canonical_pair_id(a, b)
            discovery = "sector_peer" if sec else "index_or_static"
            if static_pairs and (a, b) in [(x.upper(), y.upper()) for x, y in static_pairs]:
                discovery = "static"
            if user_pairs and (a, b) in [
                tuple(sorted((x.upper(), y.upper()))) for x, y in user_pairs
            ]:
                discovery = "user_defined"
            out[pid] = PairPanel(
                pair_id=pid,
                leg_a=a,
                leg_b=b,
                as_of=as_of,
                sector_id=str(sec) if sec else None,
                closes_a=ca,
                closes_b=cb,
                rval_meta=rval_meta,
                sources=sources,
                stale=stale,
                discovery=discovery,
            )
        return out


def _closes_from_snapshot(snapshot: FeatureSnapshot) -> list[float] | None:
    for fv in snapshot.values.values():
        bars = (fv.metadata or {}).get("closes") or (fv.metadata or {}).get("bars")
        if isinstance(bars, list) and bars:
            if isinstance(bars[0], (int, float)):
                return [float(x) for x in bars]
            if isinstance(bars[0], dict) and "close" in bars[0]:
                return [float(b["close"]) for b in bars]
    return None


def _rval_from_registry(
    registry: FeatureRegistryService,
    leg_a: str,
    leg_b: str,
    as_of: str,
) -> dict[str, float]:
    """Consume available RVAL_* metadata when materialized (optional)."""
    out: dict[str, float] = {}
    # Pair-scoped symbol key convention: PAIRID
    pair_sym = canonical_pair_id(leg_a, leg_b)
    for fid in REGISTRY_RVAL:
        fv = registry.get(fid, symbol=pair_sym, as_of=as_of, pit_mode=True)
        if fv is None:
            fv = registry.get(fid, symbol=None, as_of=as_of, pit_mode=True)
        if fv is not None and fv.value is not None:
            try:
                out[fid] = float(fv.value)
            except (TypeError, ValueError):
                continue
    return out
