"""CRE rolling metrics — IC, calibration, Brier, precision/recall, risk stats."""

from __future__ import annotations

import math
from typing import Any

from app.cre.models import ROLLING_WINDOWS, RollingMetrics
from app.validation.golden.loader import GoldenDataset
from app.validation.models import ReplayDaySlice


def build_observation_rows(
    days: list[ReplayDaySlice],
    dataset: GoldenDataset,
) -> list[dict[str, Any]]:
    """Flatten per-symbol daily observations for metric windows."""
    day_by = {d.as_of: d for d in dataset.days}
    rows: list[dict[str, Any]] = []
    for slice_ in days:
        g = day_by.get(slice_.as_of)
        if g is None:
            continue
        for sym, score in slice_.l4_scores.items():
            fwd = g.forward_returns.get(sym)
            if fwd is None:
                continue
            conf = float(slice_.confidences.get(sym, 0.5))
            label = slice_.l4_labels.get(sym, "Neutral")
            e03_score = slice_.e03_scores.get(sym)
            rows.append(
                {
                    "as_of": slice_.as_of,
                    "symbol": sym,
                    "l4_score": float(score),
                    "e03_score": float(e03_score) if e03_score is not None else None,
                    "confidence": conf,
                    "label": label,
                    "forward_return": float(fwd),
                    "pred_up": score >= 50.0,
                    "realized_up": fwd > 0.0,
                    "portfolio_return": float(slice_.portfolio_return or 0.0),
                    "benchmark_return": float(slice_.benchmark_return or 0.0),
                }
            )
    return rows


def rolling_metrics_bundle(
    days: list[ReplayDaySlice],
    dataset: GoldenDataset,
    *,
    parity_stability: float | None,
    schema_stability: float | None,
    latency_ms: float | None,
) -> dict[str, RollingMetrics]:
    rows = build_observation_rows(days, dataset)
    out: dict[str, RollingMetrics] = {}
    for window in ROLLING_WINDOWS:
        out[str(window)] = _window_metrics(
            days,
            rows,
            window=window,
            parity_stability=parity_stability,
            schema_stability=schema_stability,
            latency_ms=latency_ms,
        )
    return out


def _window_metrics(
    days: list[ReplayDaySlice],
    rows: list[dict[str, Any]],
    *,
    window: int,
    parity_stability: float | None,
    schema_stability: float | None,
    latency_ms: float | None,
) -> RollingMetrics:
    use_days = days[-min(len(days), window) :]
    asofs = {d.as_of for d in use_days}
    use_rows = [r for r in rows if r["as_of"] in asofs]
    rets = [float(d.portfolio_return or 0.0) for d in use_days]

    return RollingMetrics(
        window=window,
        days_used=len(use_days),
        information_coefficient=_ic(use_rows),
        calibration_error=_calibration_error(use_rows),
        brier_score=_brier(use_rows),
        precision=_precision(use_rows),
        recall=_recall(use_rows),
        hit_rate=_hit_rate(use_rows),
        sharpe=_sharpe(rets),
        sortino=_sortino(rets),
        max_drawdown=_max_drawdown(rets),
        turnover=_turnover(use_days),
        average_confidence=_avg([r["confidence"] for r in use_rows]),
        latency_ms=latency_ms,
        schema_stability=schema_stability,
        parity_stability=parity_stability,
    )


def _ic(rows: list[dict[str, Any]]) -> float | None:
    # Mean daily Spearman across as_of
    by_day: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_day.setdefault(r["as_of"], []).append(r)
    ics: list[float] = []
    for day_rows in by_day.values():
        if len(day_rows) < 3:
            continue
        xs = [r["l4_score"] for r in day_rows]
        ys = [r["forward_return"] for r in day_rows]
        val = _spearman(xs, ys)
        if val is not None:
            ics.append(val)
    return round(sum(ics) / len(ics), 6) if ics else None


def _calibration_error(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    # |mean confidence - hit rate|
    hits = sum(1 for r in rows if r["pred_up"] == r["realized_up"])
    hit = hits / len(rows)
    conf = sum(r["confidence"] for r in rows) / len(rows)
    return round(abs(conf - hit), 6)


def _brier(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    # Map score to probability via confidence-scaled sigmoid-ish: conf if pred_up else 1-conf
    total = 0.0
    for r in rows:
        p = r["confidence"] if r["pred_up"] else (1.0 - r["confidence"])
        y = 1.0 if r["realized_up"] else 0.0
        total += (p - y) ** 2
    return round(total / len(rows), 6)


def _precision(rows: list[dict[str, Any]]) -> float | None:
    pred_pos = [r for r in rows if r["label"] in {"Bullish", "Strong Bullish"} or r["pred_up"]]
    if not pred_pos:
        return None
    tp = sum(1 for r in pred_pos if r["realized_up"])
    return round(tp / len(pred_pos), 6)


def _recall(rows: list[dict[str, Any]]) -> float | None:
    actual_pos = [r for r in rows if r["realized_up"]]
    if not actual_pos:
        return None
    tp = sum(1 for r in actual_pos if r["pred_up"] or r["label"] in {"Bullish", "Strong Bullish"})
    return round(tp / len(actual_pos), 6)


def _hit_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r["pred_up"] == r["realized_up"]) / len(rows), 6)


def _turnover(days: list[ReplayDaySlice]) -> float | None:
    if len(days) < 2:
        return 0.0 if days else None
    turns = []
    for a, b in zip(days, days[1:]):
        syms = set(a.portfolio_weights) | set(b.portfolio_weights)
        t = 0.5 * sum(
            abs(b.portfolio_weights.get(s, 0.0) - a.portfolio_weights.get(s, 0.0)) for s in syms
        )
        turns.append(t)
    return round(sum(turns) / len(turns), 6) if turns else 0.0


def _sharpe(rets: list[float]) -> float | None:
    if len(rets) < 2:
        return None
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)
    sigma = math.sqrt(var)
    if sigma < 1e-12:
        return None
    return round((mu / sigma) * math.sqrt(252.0), 6)


def _sortino(rets: list[float]) -> float | None:
    if len(rets) < 2:
        return None
    mu = sum(rets) / len(rets)
    dvar = sum(min(0.0, r) ** 2 for r in rets) / (len(rets) - 1)
    dsigma = math.sqrt(dvar)
    if dsigma < 1e-12:
        return None
    return round((mu / dsigma) * math.sqrt(252.0), 6)


def _max_drawdown(rets: list[float]) -> float | None:
    if not rets:
        return None
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for r in rets:
        equity *= 1.0 + r
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1.0)
    return round(mdd, 6)


def _avg(vals: list[float]) -> float | None:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    rx = _rank(xs)
    ry = _rank(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    deny = math.sqrt(sum((b - my) ** 2 for b in ry))
    if denx < 1e-12 or deny < 1e-12:
        return None
    return num / (denx * deny)


def _rank(vals: list[float]) -> list[float]:
    ordered = sorted(enumerate(vals), key=lambda t: t[1])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[ordered[k][0]] = avg
        i = j + 1
    return ranks
