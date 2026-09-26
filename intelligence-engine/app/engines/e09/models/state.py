"""E09-002 Trend State Builder — horizons, vol scaling, persistence, composite CTA."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.e09.features.builder import TrendPanel


@dataclass
class TrendStateRow:
    symbol: str
    as_of: str
    sector_id: str | None
    metrics: dict[str, float]
    short_trend: float
    medium_trend: float
    long_trend: float
    ts_momentum: float
    vol_scaled_signal: float
    persistence: float
    exhaustion: float
    composite_score: float
    side: str  # long|short|flat
    label: str
    confidence: float
    stale_inputs: list[str] = field(default_factory=list)
    coverage: float = 0.0


def compute_universe_states(panels: dict[str, TrendPanel]) -> dict[str, TrendStateRow]:
    """Deterministic per-symbol CTA trend states with cross-section composite ranking."""
    symbols = sorted(panels.keys())
    if not symbols:
        return {}

    raw_signals = []
    for s in symbols:
        m = panels[s].metrics
        raw_signals.append((s, float(m.get("vol_scaled_signal", 0.0))))

    # Percentile of vol-scaled signal → 0–100 composite component
    ranked = sorted(raw_signals, key=lambda t: t[1])
    n = len(ranked)
    pct: dict[str, float] = {}
    for i, (s, _) in enumerate(ranked):
        pct[s] = 100.0 * (i + 1) / n if n > 1 else 50.0

    out: dict[str, TrendStateRow] = {}
    for sym in symbols:
        panel = panels[sym]
        m = panel.metrics
        short = float(m.get("ret_short", 0.0))
        medium = float(m.get("ret_medium", 0.0))
        long = float(m.get("ret_long", 0.0))
        ts_mom = float(m.get("ts_momentum", 0.0))
        vol_sig = float(m.get("vol_scaled_signal", 0.0))
        persistence = float(m.get("persistence", 0.0))
        exhaustion = float(m.get("exhaustion", 0.0))

        # Map signed vol-scaled signal to 0–100 via cross-section percentile,
        # then haircut by exhaustion and boost by persistence.
        base = pct.get(sym, 50.0)
        composite = round(
            max(
                0.0,
                min(
                    100.0,
                    0.55 * base
                    + 0.25 * (persistence * 100.0)
                    + 0.20 * ((1.0 - exhaustion) * 100.0),
                ),
            ),
            6,
        )
        # Directional tilt from own signal (keep ranking informative for longs/shorts)
        if vol_sig > 0:
            composite = round(min(100.0, composite + min(10.0, vol_sig * 2.0)), 6)
        elif vol_sig < 0:
            composite = round(max(0.0, composite - min(10.0, abs(vol_sig) * 2.0)), 6)

        side, label = _side_label(vol_sig, persistence, exhaustion, composite)
        coverage = _coverage(panel)
        conf = round(
            max(0.35, min(0.95, 0.50 + 0.35 * coverage + 0.15 * persistence - 0.20 * exhaustion)),
            6,
        )
        out[sym] = TrendStateRow(
            symbol=sym,
            as_of=panel.as_of,
            sector_id=panel.sector_id,
            metrics=dict(m),
            short_trend=round(short, 8),
            medium_trend=round(medium, 8),
            long_trend=round(long, 8),
            ts_momentum=round(ts_mom, 8),
            vol_scaled_signal=round(vol_sig, 8),
            persistence=round(persistence, 6),
            exhaustion=round(exhaustion, 6),
            composite_score=composite,
            side=side,
            label=label,
            confidence=conf,
            stale_inputs=list(panel.stale),
            coverage=coverage,
        )
    return out


def _side_label(
    vol_sig: float,
    persistence: float,
    exhaustion: float,
    composite: float,
) -> tuple[str, str]:
    if exhaustion >= 0.75 and abs(vol_sig) > 0.2:
        return "flat", "Trend Exhaustion"
    if vol_sig > 0.15 and persistence >= 0.45:
        return "long", "CTA Trend Long"
    if vol_sig < -0.15 and persistence >= 0.45:
        return "short", "CTA Trend Short"
    if composite >= 65:
        return "long", "CTA Mild Long"
    if composite <= 35:
        return "short", "CTA Mild Short"
    return "flat", "CTA Neutral"


def _coverage(panel: TrendPanel) -> float:
    required = ("ret_short", "ret_medium", "ret_long", "realized_vol_20", "ts_momentum", "persistence")
    hit = sum(1 for m in required if m in panel.metrics)
    return hit / len(required)
