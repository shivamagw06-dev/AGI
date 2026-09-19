"""E13-002 Composite Fundamental Scorer — Quality / Value / Growth / Balance Sheet."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.e13.features.builder import FundamentalPanel
from app.engines.e13.mapping import COMPOSITE_WEIGHTS, P0_PILLARS, PILLAR_WEIGHTS
from app.engines.e13.models.normalise import clip_loading, percentile_scores, winsorise, zscore


@dataclass
class FundamentalScoreRow:
    symbol: str
    as_of: str
    sector_id: str | None
    metrics: dict[str, float]
    pillar_raw: dict[str, float]
    pillar_z: dict[str, float]
    pillar_scores: dict[str, float]
    quality_score: float
    value_score: float
    growth_score: float
    balance_sheet_score: float
    composite_score: float
    label: str
    side: str  # long|short|flat
    confidence: float
    top_metrics: list[dict[str, float | str]] = field(default_factory=list)
    stale_inputs: list[str] = field(default_factory=list)
    coverage: float = 0.0


def compute_universe_scores(panels: dict[str, FundamentalPanel]) -> dict[str, FundamentalScoreRow]:
    """Cross-sectional pillar scores → composite fundamental score (deterministic)."""
    symbols = sorted(panels.keys())
    if not symbols:
        return {}

    # Per-metric cross-section z then weighted pillar raw z
    metric_z: dict[str, dict[str, float]] = {}
    all_metrics = sorted({m for p in panels.values() for m in p.metrics})
    for metric in all_metrics:
        vals = [panels[s].metrics.get(metric) for s in symbols]
        present_idx = [i for i, v in enumerate(vals) if v is not None]
        if len(present_idx) < 2:
            for s in symbols:
                if metric in panels[s].metrics:
                    metric_z.setdefault(s, {})[metric] = 0.0
            continue
        series = [float(vals[i]) for i in present_idx]  # type: ignore[arg-type]
        w = winsorise(series)
        z = zscore(w)
        for j, i in enumerate(present_idx):
            metric_z.setdefault(symbols[i], {})[metric] = float(z[j] or 0.0)

    pillar_raw: dict[str, dict[str, float | None]] = {p: {} for p in P0_PILLARS}
    for pillar, specs in PILLAR_WEIGHTS.items():
        for sym in symbols:
            num = 0.0
            den = 0.0
            for metric, weight, invert in specs:
                if metric not in metric_z.get(sym, {}):
                    continue
                z = metric_z[sym][metric]
                if invert:
                    z = -z
                num += weight * z
                den += weight
            pillar_raw[pillar][sym] = (num / den) if den > 0 else None

    pillar_scores: dict[str, dict[str, float]] = {p: {} for p in P0_PILLARS}
    pillar_z_out: dict[str, dict[str, float]] = {p: {} for p in P0_PILLARS}
    for pillar in P0_PILLARS:
        series = [pillar_raw[pillar][s] for s in symbols]
        # already z-like; re-winsorise across names then percentile
        present = [(i, v) for i, v in enumerate(series) if v is not None]
        z_list: list[float | None] = [None] * len(symbols)
        if present:
            vals = [float(v) for _, v in present]
            w = winsorise(vals)
            zz = zscore(w)
            for j, (i, _) in enumerate(present):
                z_list[i] = zz[j]
        pct = percentile_scores(z_list)
        for i, sym in enumerate(symbols):
            if z_list[i] is None:
                continue
            pillar_z_out[pillar][sym] = clip_loading(float(z_list[i]))
            pillar_scores[pillar][sym] = float(pct[i] if pct[i] is not None else 50.0)

    out: dict[str, FundamentalScoreRow] = {}
    for sym in symbols:
        panel = panels[sym]
        scores = {p: pillar_scores[p].get(sym, 50.0) for p in P0_PILLARS}
        raw_z = {p: pillar_z_out[p].get(sym, 0.0) for p in P0_PILLARS}
        composite = 0.0
        wsum = 0.0
        for p, w in COMPOSITE_WEIGHTS.items():
            if p in scores:
                composite += w * scores[p]
                wsum += w
        composite = round(composite / wsum if wsum else 50.0, 6)
        coverage = _coverage(panel)
        conf = round(max(0.35, min(0.95, 0.55 + 0.4 * coverage - 0.03 * len(panel.stale))), 6)
        label, side = _label_side(composite)
        top = _top_metrics(panel.metrics, metric_z.get(sym, {}))
        out[sym] = FundamentalScoreRow(
            symbol=sym,
            as_of=panel.as_of,
            sector_id=panel.sector_id,
            metrics=dict(panel.metrics),
            pillar_raw={p: float(pillar_raw[p][sym]) for p in P0_PILLARS if pillar_raw[p].get(sym) is not None},
            pillar_z=raw_z,
            pillar_scores=scores,
            quality_score=round(scores["QUALITY"], 6),
            value_score=round(scores["VALUE"], 6),
            growth_score=round(scores["GROWTH"], 6),
            balance_sheet_score=round(scores["BALANCE_SHEET"], 6),
            composite_score=composite,
            label=label,
            side=side,
            confidence=conf,
            top_metrics=top,
            stale_inputs=list(panel.stale),
            coverage=coverage,
        )
    return out


def _coverage(panel: FundamentalPanel) -> float:
    required = (
        "revenue_growth",
        "eps_growth",
        "gross_margin",
        "oper_margin",
        "roe",
        "roic",
        "roce",
        "leverage",
        "fcf_yield",
        "ep_ttm",
    )
    hit = sum(1 for m in required if m in panel.metrics)
    return hit / len(required)


def _label_side(score: float) -> tuple[str, str]:
    if score >= 70:
        return "Strong Fundamental Long", "long"
    if score >= 55:
        return "Fundamental Long", "long"
    if score <= 30:
        return "Strong Fundamental Short", "short"
    if score <= 45:
        return "Fundamental Short", "short"
    return "Neutral", "flat"


def _top_metrics(metrics: dict[str, float], zmap: dict[str, float]) -> list[dict[str, float | str]]:
    ranked = sorted(zmap.items(), key=lambda kv: abs(kv[1]), reverse=True)
    out: list[dict[str, float | str]] = []
    for metric, z in ranked[:5]:
        out.append({"metric": metric, "value": metrics.get(metric, 0.0), "z": round(z, 6)})
    return out
