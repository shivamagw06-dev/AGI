"""Alpha research, statistical validation and walk-forward analysis."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence


FORWARD_HORIZONS = (21, 63, 126, 252)


def _rank(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        average = (cursor + end - 1) / 2.0 + 1.0
        for idx in range(cursor, end):
            ranks[indexed[idx][0]] = average
        cursor = end
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 3:
        return None
    rx, ry = _rank(x), _rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return numerator / denominator if denominator else None


def _decile(value: float, ordered: Sequence[float]) -> int:
    if not ordered:
        return 0
    position = sum(1 for item in ordered if item < value)
    return min(9, int(10 * position / len(ordered))) + 1


def _mean(values: Sequence[float]) -> float | None:
    return statistics.mean(values) if values else None


def evaluate_factor(rows: Iterable[Mapping[str, Any]], *, feature_id: str) -> dict[str, Any]:
    """Evaluate one feature independently using cross-sectional date cohorts."""
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        row = dict(raw)
        if row.get("feature_id") != feature_id:
            continue
        if row.get("feature_value") is None:
            row["feature_value"] = row.get("value")
        by_date[str(row.get("signal_date") or row.get("as_of"))].append(row)

    daily_ic: dict[int, list[float]] = {horizon: [] for horizon in FORWARD_HORIZONS}
    deciles: dict[int, dict[int, list[float]]] = {
        horizon: {bucket: [] for bucket in range(1, 11)} for horizon in FORWARD_HORIZONS
    }
    regime_ic: dict[str, dict[int, list[float]]] = defaultdict(lambda: {h: [] for h in FORWARD_HORIZONS})
    observations = 0
    for day, cohort in sorted(by_date.items()):
        clean = [row for row in cohort if row.get("feature_value") is not None]
        features = [float(row["feature_value"]) for row in clean]
        ordered = sorted(features)
        observations += len(clean)
        for horizon in FORWARD_HORIZONS:
            key = f"forward_return_{horizon}d"
            paired = [(float(row["feature_value"]), float(row[key]), row) for row in clean if row.get(key) is not None]
            if len(paired) < 3:
                continue
            ic = spearman([item[0] for item in paired], [item[1] for item in paired])
            if ic is not None:
                daily_ic[horizon].append(ic)
                regime = str(paired[0][2].get("regime") or "UNCLASSIFIED")
                regime_ic[regime][horizon].append(ic)
            for feature, forward, _ in paired:
                deciles[horizon][_decile(feature, ordered)].append(forward)

    horizon_results = {}
    for horizon in FORWARD_HORIZONS:
        ic_values = daily_ic[horizon]
        low = deciles[horizon][1]
        high = deciles[horizon][10]
        spread = None
        if low and high:
            spread = statistics.mean(high) - statistics.mean(low)
        horizon_results[f"{horizon}d"] = {
            "mean_ic": _mean(ic_values),
            "median_ic": statistics.median(ic_values) if ic_values else None,
            "ic_hit_rate": sum(value > 0 for value in ic_values) / len(ic_values) if ic_values else None,
            "independent_dates": len(ic_values),
            "decile_1_return": _mean(low),
            "decile_10_return": _mean(high),
            "long_short_spread": spread,
            "deciles": {str(bucket): _mean(values) for bucket, values in deciles[horizon].items()},
        }

    regimes = {
        regime: {f"{horizon}d_mean_ic": _mean(values) for horizon, values in horizons.items()}
        for regime, horizons in regime_ic.items()
    }
    return {
        "feature_id": feature_id,
        "observations": observations,
        "independent_signal_dates": len(by_date),
        "horizons": horizon_results,
        "regimes": regimes,
        "claim": "historical_factor_research_only",
        "validated": False,
        "validation_note": "Promotion requires pre-registered thresholds and out-of-sample evidence.",
    }


def walk_forward_partitions(dates: Sequence[str], *, train: float = 0.6, validate: float = 0.2) -> dict[str, list[str]]:
    ordered = sorted(set(str(value) for value in dates))
    if len(ordered) < 5:
        return {"train": ordered, "validation": [], "test": []}
    train_end = max(1, int(len(ordered) * train))
    validation_end = max(train_end + 1, int(len(ordered) * (train + validate)))
    return {
        "train": ordered[:train_end],
        "validation": ordered[train_end:validation_end],
        "test": ordered[validation_end:],
    }


def parameter_stability(results: Sequence[Mapping[str, Any]], metric: str = "net_return") -> dict[str, Any]:
    values = [float(row[metric]) for row in results if row.get(metric) is not None]
    if len(values) < 3:
        return {"state": "MISSING", "reason": "at_least_three_parameter_runs_required"}
    mean = statistics.mean(values)
    dispersion = statistics.pstdev(values)
    return {
        "state": "PASSED" if mean > 0 and sum(value > 0 for value in values) / len(values) >= 0.67 else "FAILED",
        "runs": len(values),
        "mean": mean,
        "dispersion": dispersion,
        "positive_share": sum(value > 0 for value in values) / len(values),
    }
