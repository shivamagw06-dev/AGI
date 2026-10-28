"""Exposure calculator — factor z, scores, loadings, confidence (P0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e02.features.builder import SymbolPanel
from app.engines.e02.mapping import FACTOR_FEATURE_IDS, FACTOR_NORM, FACTOR_WEIGHTS, P0_FACTORS
from app.engines.e02.models.normalise import clip_loading, percentile_scores, sector_or_universe_z


@dataclass
class FactorExposureRow:
    symbol: str
    as_of: str
    sector_id: str | None
    scores: dict[str, float]
    loadings: dict[str, float]
    raw_factor_z: dict[str, float]
    factor_confidence: dict[str, float]
    factor_features: dict[str, float]  # FACTOR_* intermediate
    composite_score: float
    dominant_factor: str
    style_box: dict[str, str]
    overall_confidence: float
    top_metrics: list[dict[str, Any]] = field(default_factory=list)
    stale_inputs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def compute_universe_exposures(panels: dict[str, SymbolPanel]) -> dict[str, FactorExposureRow]:
    """Cross-sectional P0 exposures for all symbols in the panel set."""
    if not panels:
        return {}
    symbols = sorted(panels.keys())
    sectors = [panels[s].sector_id for s in symbols]
    n = len(symbols)

    # Metric matrix
    all_metrics: set[str] = set()
    for p in panels.values():
        all_metrics |= set(p.metrics.keys())

    metric_z: dict[str, list[float | None]] = {}
    for metric in sorted(all_metrics):
        # Choose norm mode from first factor that uses it; default sector
        mode = "sector"
        for fid, weights in FACTOR_WEIGHTS.items():
            if any(m == metric for m, _, _ in weights):
                mode = FACTOR_NORM.get(fid, "sector")
                break
        raw = [panels[s].metrics.get(metric) for s in symbols]
        # Convert missing to None explicitly
        raw_n = [float(v) if v is not None else None for v in raw]
        metric_z[metric] = sector_or_universe_z(raw_n, sectors, mode=mode)

    # Factor z per symbol
    factor_z: dict[str, list[float | None]] = {f: [None] * n for f in P0_FACTORS}
    factor_cov: dict[str, list[float]] = {f: [0.0] * n for f in P0_FACTORS}

    for f in P0_FACTORS:
        weights = FACTOR_WEIGHTS[f]
        for i, sym in enumerate(symbols):
            parts: list[tuple[float, float]] = []
            present = 0
            for metric, w, invert in weights:
                z_list = metric_z.get(metric)
                if z_list is None or z_list[i] is None:
                    continue
                z = float(z_list[i])  # type: ignore[arg-type]
                if invert:
                    z = -z
                parts.append((w, z))
                present += 1
            if not parts:
                factor_z[f][i] = None
                factor_cov[f][i] = 0.0
                continue
            wsum = sum(w for w, _ in parts)
            zf = sum(w * z for w, z in parts) / wsum
            factor_z[f][i] = zf
            factor_cov[f][i] = present / len(weights)

    factor_scores: dict[str, list[float | None]] = {
        f: percentile_scores(factor_z[f]) for f in P0_FACTORS
    }

    rows: dict[str, FactorExposureRow] = {}
    for i, sym in enumerate(symbols):
        scores: dict[str, float] = {}
        loadings: dict[str, float] = {}
        raw_z: dict[str, float] = {}
        conf: dict[str, float] = {}
        feats: dict[str, float] = {}
        for f in P0_FACTORS:
            z = factor_z[f][i]
            sc = factor_scores[f][i]
            if z is None or sc is None:
                continue
            scores[f] = float(round(sc, 4))
            loadings[f] = float(round(clip_loading(z), 4))
            raw_z[f] = float(round(z, 6))
            conf[f] = float(round(max(0.0, min(1.0, 0.4 + 0.6 * factor_cov[f][i])), 4))
            feats[FACTOR_FEATURE_IDS[f]] = scores[f]

        if scores:
            composite = sum(scores.values()) / len(scores)
            dominant = max(scores.items(), key=lambda kv: kv[1])[0]
            overall = sum(conf.values()) / len(conf)
        else:
            composite = 50.0
            dominant = "F_QUALITY"
            overall = 0.0

        style_box = _style_box(scores)
        top_metrics = _top_metrics(panels[sym], metric_z, symbols, i)
        stale = list(panels[sym].stale)
        # Attach intermediate FACTOR_* on panel for audit
        panels[sym].factor_raw = dict(feats)

        rows[sym] = FactorExposureRow(
            symbol=sym,
            as_of=panels[sym].as_of,
            sector_id=panels[sym].sector_id,
            scores=scores,
            loadings=loadings,
            raw_factor_z=raw_z,
            factor_confidence=conf,
            factor_features=feats,
            composite_score=float(round(composite, 4)),
            dominant_factor=dominant,
            style_box=style_box,
            overall_confidence=float(round(overall, 4)),
            top_metrics=top_metrics,
            stale_inputs=stale,
            metadata={"sources": panels[sym].sources, "missing": panels[sym].missing},
        )
    return rows


def _style_box(scores: dict[str, float]) -> dict[str, str]:
    size_s = scores.get("F_SIZE", 50.0)
    # High F_SIZE = small; invert for box
    if size_s >= 66:
        size = "small"
    elif size_s <= 33:
        size = "large"
    else:
        size = "mid"
    val = scores.get("F_VALUE", 50.0)
    mom = scores.get("F_MOMENTUM", 50.0)
    # value vs growth proxy: growth ~ momentum when Growth factor absent in P0
    style_signal = mom - val
    if style_signal > 15:
        style = "growth"
    elif style_signal < -15:
        style = "value"
    else:
        style = "growth_blend" if mom >= val else "value_blend"
    return {"size": size, "style": style}


def _top_metrics(
    panel: SymbolPanel,
    metric_z: dict[str, list[float | None]],
    symbols: list[str],
    idx: int,
) -> list[dict[str, Any]]:
    items: list[tuple[str, float]] = []
    for metric, zlist in metric_z.items():
        z = zlist[idx]
        if z is None:
            continue
        if metric in panel.metrics:
            items.append((metric, float(z)))
    items.sort(key=lambda t: abs(t[1]), reverse=True)
    return [{"metric": m, "z": round(z, 3)} for m, z in items[:3]]
