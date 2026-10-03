"""AIP validation metrics and deltas vs research baselines."""

from __future__ import annotations

import math
import random
from typing import Any

from app.aip.models import MetricBundle, MetricDeltas
from app.validation.golden.loader import GoldenDataset
from app.validation.models import ReplayDaySlice


def _avg(vals: list[float]) -> float | None:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)


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


def paper_portfolio_returns(
    scored: list[dict[str, Any]],
    dataset: GoldenDataset,
) -> tuple[list[float], float | None]:
    """Long score>=55 / short score<=45 equal-weight paper book; turnover vs prior day."""
    day_by = {d.as_of: d for d in dataset.days}
    by_asof: dict[str, list[dict[str, Any]]] = {}
    for row in scored:
        by_asof.setdefault(row["as_of"], []).append(row)

    rets: list[float] = []
    prev_w: dict[str, float] = {}
    turns: list[float] = []
    for as_of in sorted(by_asof):
        g = day_by.get(as_of)
        if g is None:
            continue
        longs = [r for r in by_asof[as_of] if r["score"] >= 55.0]
        shorts = [r for r in by_asof[as_of] if r["score"] <= 45.0]
        weights: dict[str, float] = {}
        if longs:
            w = 1.0 / len(longs)
            for r in longs:
                weights[r["symbol"]] = weights.get(r["symbol"], 0.0) + w
        if shorts:
            w = 1.0 / len(shorts)
            for r in shorts:
                weights[r["symbol"]] = weights.get(r["symbol"], 0.0) - w
        # Normalize gross exposure to 1 when both sides present
        gross = sum(abs(v) for v in weights.values()) or 1.0
        weights = {k: v / gross for k, v in weights.items()}
        day_ret = 0.0
        for sym, w in weights.items():
            day_ret += w * float(g.forward_returns.get(sym, 0.0))
        rets.append(day_ret)
        if prev_w:
            syms = set(prev_w) | set(weights)
            turns.append(
                0.5 * sum(abs(weights.get(s, 0.0) - prev_w.get(s, 0.0)) for s in syms)
            )
        prev_w = weights
    turnover = round(sum(turns) / len(turns), 6) if turns else (0.0 if rets else None)
    return rets, turnover


def metrics_from_scored(
    scored: list[dict[str, Any]],
    dataset: GoldenDataset,
) -> MetricBundle:
    day_by = {d.as_of: d for d in dataset.days}
    rows: list[dict[str, Any]] = []
    for r in scored:
        g = day_by.get(r["as_of"])
        if g is None:
            continue
        fwd = g.forward_returns.get(r["symbol"])
        if fwd is None:
            continue
        pred_up = r["score"] >= 50.0
        realized_up = float(fwd) > 0.0
        rows.append(
            {
                **r,
                "forward_return": float(fwd),
                "pred_up": pred_up,
                "realized_up": realized_up,
                "correct": pred_up == realized_up,
            }
        )

    by_day: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_day.setdefault(r["as_of"], []).append(r)
    ics: list[float] = []
    for day_rows in by_day.values():
        if len(day_rows) < 3:
            continue
        val = _spearman(
            [x["score"] for x in day_rows],
            [x["forward_return"] for x in day_rows],
        )
        if val is not None:
            ics.append(val)

    hit = (
        sum(1 for r in rows if r["correct"]) / len(rows) if rows else None
    )
    conf = _avg([float(r["confidence"]) for r in rows])
    cal = abs(conf - hit) if conf is not None and hit is not None else None
    rets, turnover = paper_portfolio_returns(scored, dataset)

    return MetricBundle(
        sharpe=_sharpe(rets),
        sortino=_sortino(rets),
        information_coefficient=round(sum(ics) / len(ics), 6) if ics else None,
        hit_rate=round(hit, 6) if hit is not None else None,
        calibration_error=round(cal, 6) if cal is not None else None,
        max_drawdown=_max_drawdown(rets),
        turnover=turnover,
        prediction_accuracy=round(hit, 6) if hit is not None else None,
        n_observations=len(rows),
        n_days=len(by_day),
    )


def metrics_from_replay_l4(
    days: list[ReplayDaySlice],
    dataset: GoldenDataset,
) -> MetricBundle:
    scored = [
        {
            "as_of": d.as_of,
            "symbol": sym,
            "score": float(score),
            "label": d.l4_labels.get(sym, "Neutral"),
            "confidence": float(d.confidences.get(sym, 0.5)),
        }
        for d in days
        for sym, score in d.l4_scores.items()
    ]
    return metrics_from_scored(scored, dataset)


def metrics_from_replay_e03(
    days: list[ReplayDaySlice],
    dataset: GoldenDataset,
) -> MetricBundle:
    scored = [
        {
            "as_of": d.as_of,
            "symbol": sym,
            "score": float(score),
            "label": d.e03_labels.get(sym, "Neutral"),
            "confidence": float(d.confidences.get(sym, 0.5)),
        }
        for d in days
        for sym, score in d.e03_scores.items()
    ]
    return metrics_from_scored(scored, dataset)


def delta(candidate: MetricBundle, baseline: MetricBundle) -> MetricDeltas:
    def d(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return round(a - b, 6)

    # Lower calibration_error and less-negative max_drawdown are improvements.
    # We report raw deltas (candidate - baseline).
    return MetricDeltas(
        sharpe_delta=d(candidate.sharpe, baseline.sharpe),
        sortino_delta=d(candidate.sortino, baseline.sortino),
        ic_delta=d(candidate.information_coefficient, baseline.information_coefficient),
        hit_rate_delta=d(candidate.hit_rate, baseline.hit_rate),
        calibration_delta=d(candidate.calibration_error, baseline.calibration_error),
        max_drawdown_delta=d(candidate.max_drawdown, baseline.max_drawdown),
        turnover_delta=d(candidate.turnover, baseline.turnover),
        prediction_accuracy_delta=d(
            candidate.prediction_accuracy, baseline.prediction_accuracy
        ),
    )


def bootstrap_ic_pvalue(
    scored_a: list[dict[str, Any]],
    scored_b: list[dict[str, Any]],
    dataset: GoldenDataset,
    *,
    n_bootstrap: int = 200,
    seed: int = 42,
) -> tuple[float | None, bool]:
    """Paired day-level bootstrap on IC difference (A - B). Significant if p < 0.05."""
    day_by = {d.as_of: d for d in dataset.days}

    def day_ic(scored: list[dict[str, Any]], as_of: str) -> float | None:
        g = day_by.get(as_of)
        if g is None:
            return None
        rows = [r for r in scored if r["as_of"] == as_of]
        pairs = [
            (float(r["score"]), float(g.forward_returns[r["symbol"]]))
            for r in rows
            if r["symbol"] in g.forward_returns
        ]
        if len(pairs) < 3:
            return None
        return _spearman([p[0] for p in pairs], [p[1] for p in pairs])

    asofs = sorted({r["as_of"] for r in scored_a} & {r["as_of"] for r in scored_b})
    diffs: list[float] = []
    for a in asofs:
        ia = day_ic(scored_a, a)
        ib = day_ic(scored_b, a)
        if ia is not None and ib is not None:
            diffs.append(ia - ib)
    if len(diffs) < 2:
        return None, False
    rng = random.Random(seed)
    obs = sum(diffs) / len(diffs)
    count = 0
    for _ in range(n_bootstrap):
        sample = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
        if (sum(sample) / len(sample)) <= 0:
            count += 1
    # one-sided: candidate better than baseline
    p = (count + 1) / (n_bootstrap + 1)
    return round(p, 6), bool(obs > 0 and p < 0.05)
