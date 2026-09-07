"""BT-004 Metrics Engine — performance, calibration, parity stability."""

from __future__ import annotations

import math
from typing import Any

from app.validation.golden.loader import GoldenDataset
from app.validation.models import (
    CalibrationReport,
    PerformanceReport,
    ReplayDaySlice,
    ValidationSummary,
)


def compute_metrics(
    *,
    run_id: str,
    dataset: GoldenDataset,
    days: list[ReplayDaySlice],
    engine_versions: dict[str, str],
    formula_versions: dict[str, str],
    parity_stability: float,
    deterministic: bool,
) -> ValidationSummary:
    perf = _performance(days, dataset)
    calib = _calibration(days, dataset)
    notes: list[str] = []
    if deterministic:
        notes.append("replay_deterministic")
    if parity_stability >= 0.99:
        notes.append("parity_stable")
    passed = deterministic and parity_stability >= 0.99 and len(days) == len(dataset.days)
    return ValidationSummary(
        run_id=run_id,
        dataset_id=dataset.dataset_id,
        deterministic=deterministic,
        parity_stability=parity_stability,
        n_days=len(days),
        n_symbols=len(dataset.symbols),
        performance=perf,
        calibration=calib,
        engine_versions=engine_versions,
        formula_versions=formula_versions,
        production_influence=False,
        passed=passed,
        notes=notes,
    )


def _performance(days: list[ReplayDaySlice], dataset: GoldenDataset) -> PerformanceReport:
    rets = [float(d.portfolio_return or 0.0) for d in days]
    bench = [float(d.benchmark_return or 0.0) for d in days]
    cum = _cum_return(rets)
    bcum = _cum_return(bench)
    sharpe = _sharpe(rets)
    sortino = _sortino(rets)
    mdd = _max_drawdown(rets)
    turnover = _turnover(days)
    hit = _hit_rate(days, dataset)
    win = _win_rate(rets)
    ic = _information_coefficient(days, dataset)
    avg_conf = _avg_confidence(days)
    return PerformanceReport(
        daily_returns=rets,
        benchmark_returns=bench,
        cumulative_return=round(cum, 8),
        benchmark_cumulative_return=round(bcum, 8),
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=mdd,
        turnover=turnover,
        hit_rate=hit,
        win_rate=win,
        information_coefficient=ic,
        average_confidence=avg_conf,
    )


def _calibration(days: list[ReplayDaySlice], dataset: GoldenDataset) -> CalibrationReport:
    """Bucket L4 confidence vs realized directional hit; label bucket accuracy."""
    # Confidence buckets
    edges = [0.0, 0.5, 0.6, 0.7, 0.8, 1.01]
    labels = ["<0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", ">=0.8"]
    buckets: list[dict[str, Any]] = [
        {"bucket": labels[i], "n": 0, "hits": 0, "avg_confidence": 0.0, "hit_rate": None}
        for i in range(len(labels))
    ]
    conf_sums = [0.0] * len(labels)
    label_hits = 0
    label_n = 0

    day_by_asof = {d.as_of: d for d in dataset.days}
    for slice_ in days:
        gday = day_by_asof.get(slice_.as_of)
        if gday is None:
            continue
        for sym, conf in slice_.confidences.items():
            fwd = gday.forward_returns.get(sym)
            if fwd is None:
                continue
            score = slice_.l4_scores.get(sym, 50.0)
            pred_up = score >= 50.0
            realized_up = fwd > 0
            hit = pred_up == realized_up
            # confidence bucket
            idx = 0
            for j in range(len(edges) - 1):
                if edges[j] <= conf < edges[j + 1]:
                    idx = j
                    break
            buckets[idx]["n"] += 1
            conf_sums[idx] += conf
            if hit:
                buckets[idx]["hits"] += 1
            # label bucket accuracy (bullish labels vs positive return)
            lab = slice_.l4_labels.get(sym)
            if lab in {"Bullish", "Strong Bullish", "Bearish", "Strong Bearish"}:
                label_n += 1
                bullish = lab in {"Bullish", "Strong Bullish"}
                if bullish == realized_up:
                    label_hits += 1

    for i, b in enumerate(buckets):
        if b["n"]:
            b["avg_confidence"] = round(conf_sums[i] / b["n"], 4)
            b["hit_rate"] = round(b["hits"] / b["n"], 4)
        b.pop("hits", None)

    # Calibration error: mean |hit_rate - avg_confidence| over non-empty buckets
    errs = []
    for b in buckets:
        if b["n"] and b["hit_rate"] is not None:
            errs.append(abs(b["hit_rate"] - b["avg_confidence"]))
    cal_err = round(sum(errs) / len(errs), 6) if errs else None
    bucket_acc = round(label_hits / label_n, 6) if label_n else None
    return CalibrationReport(
        buckets=buckets,
        bucket_accuracy=bucket_acc,
        confidence_calibration_error=cal_err,
        n_observations=label_n,
    )


def _cum_return(rets: list[float]) -> float:
    x = 1.0
    for r in rets:
        x *= 1.0 + r
    return x - 1.0


def _sharpe(rets: list[float], ann: float = 252.0) -> float | None:
    if len(rets) < 2:
        return None
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)
    sigma = math.sqrt(var)
    if sigma < 1e-12:
        return None
    return round((mu / sigma) * math.sqrt(ann), 6)


def _sortino(rets: list[float], ann: float = 252.0) -> float | None:
    if len(rets) < 2:
        return None
    mu = sum(rets) / len(rets)
    downside = [min(0.0, r) ** 2 for r in rets]
    dvar = sum(downside) / (len(rets) - 1)
    dsigma = math.sqrt(dvar)
    if dsigma < 1e-12:
        return None
    return round((mu / dsigma) * math.sqrt(ann), 6)


def _max_drawdown(rets: list[float]) -> float | None:
    if not rets:
        return None
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for r in rets:
        equity *= 1.0 + r
        peak = max(peak, equity)
        dd = (equity / peak) - 1.0
        mdd = min(mdd, dd)
    return round(mdd, 6)


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


def _hit_rate(days: list[ReplayDaySlice], dataset: GoldenDataset) -> float | None:
    day_by = {d.as_of: d for d in dataset.days}
    hits = 0
    n = 0
    for slice_ in days:
        g = day_by.get(slice_.as_of)
        if g is None:
            continue
        for sym, score in slice_.l4_scores.items():
            fwd = g.forward_returns.get(sym)
            if fwd is None:
                continue
            n += 1
            if (score >= 50 and fwd > 0) or (score < 50 and fwd < 0):
                hits += 1
    return round(hits / n, 6) if n else None


def _win_rate(rets: list[float]) -> float | None:
    if not rets:
        return None
    return round(sum(1 for r in rets if r > 0) / len(rets), 6)


def _information_coefficient(days: list[ReplayDaySlice], dataset: GoldenDataset) -> float | None:
    """Mean cross-sectional Spearman IC of L4 scores vs forward returns."""
    day_by = {d.as_of: d for d in dataset.days}
    ics: list[float] = []
    for slice_ in days:
        g = day_by.get(slice_.as_of)
        if g is None:
            continue
        pairs = [
            (slice_.l4_scores[s], g.forward_returns[s])
            for s in slice_.l4_scores
            if s in g.forward_returns
        ]
        if len(pairs) < 3:
            continue
        ic = _spearman([p[0] for p in pairs], [p[1] for p in pairs])
        if ic is not None:
            ics.append(ic)
    if not ics:
        return None
    return round(sum(ics) / len(ics), 6)


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


def _avg_confidence(days: list[ReplayDaySlice]) -> float | None:
    vals = [c for d in days for c in d.confidences.values()]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)
