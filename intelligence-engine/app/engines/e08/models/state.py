"""E08-002 Volatility State Builder — regime / expansion / compression / composite."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.e08.features.builder import VolatilityPanel


@dataclass
class VolatilityStateRow:
    symbol: str
    as_of: str
    sector_id: str | None
    metrics: dict[str, float]
    realized_vol: float
    historical_vol: float
    vol_regime: str
    expansion: bool
    compression: bool
    expansion_score: float
    compression_score: float
    expected_move: float | None
    composite_score: float
    label: str
    confidence: float
    stale_inputs: list[str] = field(default_factory=list)
    coverage: float = 0.0


def compute_universe_states(panels: dict[str, VolatilityPanel]) -> dict[str, VolatilityStateRow]:
    """Deterministic per-symbol volatility states (cross-section for composite ranking)."""
    symbols = sorted(panels.keys())
    if not symbols:
        return {}

    # Cross-section percentile of realized vol for composite component
    rv_vals = [(s, panels[s].metrics.get("realized_vol_20")) for s in symbols]
    present = [(s, float(v)) for s, v in rv_vals if v is not None]
    pct: dict[str, float] = {}
    if present:
        ranked = sorted(present, key=lambda t: t[1])
        n = len(ranked)
        for i, (s, _) in enumerate(ranked):
            pct[s] = 100.0 * (i + 1) / n if n > 1 else 50.0

    out: dict[str, VolatilityStateRow] = {}
    for sym in symbols:
        panel = panels[sym]
        m = panel.metrics
        rv = float(m.get("realized_vol_20") or m.get("hist_vol_60") or 0.20)
        hv = float(m.get("hist_vol_60") or rv)
        ratio = float(m.get("vol_ratio") or (rv / max(hv, 1e-6)))
        exp_score = float(m.get("expansion_score") or 50.0)
        cmp_score = float(m.get("compression_score") or 50.0)
        regime = _regime(rv, ratio)
        expansion = regime == "expansion" or (ratio >= 1.15 and exp_score >= 55)
        compression = regime == "compression" or (ratio <= 0.85 and cmp_score >= 55)
        em = m.get("expected_move")
        vol_pct = pct.get(sym, 50.0)
        # Composite: higher = more elevated / unstable vol environment
        composite = round(
            0.45 * vol_pct
            + 0.30 * max(0.0, min(100.0, exp_score))
            + 0.15 * (100.0 - max(0.0, min(100.0, cmp_score)))
            + 0.10 * _regime_score(regime),
            6,
        )
        coverage = _coverage(panel)
        conf = round(max(0.35, min(0.95, 0.55 + 0.4 * coverage - 0.03 * len(panel.stale))), 6)
        out[sym] = VolatilityStateRow(
            symbol=sym,
            as_of=panel.as_of,
            sector_id=panel.sector_id,
            metrics=dict(m),
            realized_vol=round(rv, 8),
            historical_vol=round(hv, 8),
            vol_regime=regime,
            expansion=expansion,
            compression=compression,
            expansion_score=round(exp_score, 6),
            compression_score=round(cmp_score, 6),
            expected_move=None if em is None else round(float(em), 8),
            composite_score=composite,
            label=_label(regime, expansion, compression),
            confidence=conf,
            stale_inputs=list(panel.stale),
            coverage=coverage,
        )
    return out


def _regime(rv: float, ratio: float) -> str:
    if rv >= 0.45 or ratio >= 1.40:
        return "extreme"
    if ratio >= 1.15 or rv >= 0.30:
        return "expansion"
    if ratio <= 0.85 or rv <= 0.12:
        return "compression"
    return "normal"


def _regime_score(regime: str) -> float:
    return {"compression": 20.0, "normal": 45.0, "expansion": 75.0, "extreme": 95.0}.get(regime, 50.0)


def _label(regime: str, expansion: bool, compression: bool) -> str:
    if regime == "extreme":
        return "Extreme Volatility"
    if expansion:
        return "Volatility Expansion"
    if compression:
        return "Volatility Compression"
    return "Normal Volatility"


def _coverage(panel: VolatilityPanel) -> float:
    required = ("realized_vol_20", "hist_vol_60", "vol_ratio", "expansion_score", "compression_score")
    hit = sum(1 for m in required if m in panel.metrics)
    return hit / len(required)
