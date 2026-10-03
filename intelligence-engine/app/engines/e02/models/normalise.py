"""Cross-sectional winsorise / z-score / percentile (spec §7.1–7.2)."""

from __future__ import annotations

import math
from collections import defaultdict


def _quantile(ordered: list[float], q: float) -> float:
    """Linear-interpolation quantile on a sorted finite series."""
    n = len(ordered)
    if n == 1:
        return ordered[0]
    pos = max(0.0, min(1.0, q)) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    w = pos - lo
    return ordered[lo] * (1.0 - w) + ordered[hi] * w


def winsorise(values: list[float], lo_q: float = 0.025, hi_q: float = 0.975) -> list[float]:
    if not values:
        return []
    ordered = sorted(values)
    lo = _quantile(ordered, lo_q)
    hi = _quantile(ordered, hi_q)
    if hi < lo:
        lo, hi = hi, lo
    return [min(hi, max(lo, v)) for v in values]


def zscore(values: list[float], eps: float = 1e-8) -> list[float | None]:
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return [0.0 if v is not None else None for v in values]
    mu = sum(present) / len(present)
    var = sum((v - mu) ** 2 for v in present) / len(present)
    sigma = math.sqrt(var) + eps
    return [(v - mu) / sigma if v is not None else None for v in values]


def percentile_scores(z_values: list[float | None]) -> list[float | None]:
    """Map z to 0–100 via cross-sectional percentile rank of non-null z."""
    indexed = [(i, z) for i, z in enumerate(z_values) if z is not None]
    if not indexed:
        return [None] * len(z_values)
    if len(indexed) == 1:
        out: list[float | None] = [None] * len(z_values)
        out[indexed[0][0]] = 50.0
        return out
    ranked = sorted(indexed, key=lambda t: t[1])
    out = [None] * len(z_values)
    n = len(ranked)
    for rank, (i, _) in enumerate(ranked):
        out[i] = 100.0 * (rank + 1) / n
    return out


def group_indices(sectors: list[str | None]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for i, sec in enumerate(sectors):
        key = sec or "__UNIVERSE__"
        groups[key].append(i)
    return groups


def sector_or_universe_z(
    raw: list[float | None],
    sectors: list[str | None],
    *,
    mode: str,
) -> list[float | None]:
    """Winsorise + z within sector (or full universe)."""
    n = len(raw)
    out: list[float | None] = [None] * n
    if mode == "universe":
        idxs = [i for i, v in enumerate(raw) if v is not None]
        vals = [raw[i] for i in idxs]  # type: ignore[misc]
        w = winsorise(vals)
        z = zscore(w)
        for j, i in enumerate(idxs):
            out[i] = z[j]
        return out

    # sector mode with universe fallback for tiny buckets
    groups = group_indices(sectors)
    for _key, idxs in groups.items():
        present = [i for i in idxs if raw[i] is not None]
        if len(present) < 3:
            # fallback: defer to universe pass later
            continue
        vals = [raw[i] for i in present]  # type: ignore[misc]
        w = winsorise(vals)
        z = zscore(w)
        for j, i in enumerate(present):
            out[i] = z[j]

    # Fill any still-missing with universe z
    missing = [i for i, v in enumerate(out) if raw[i] is not None and v is None]
    if missing:
        vals = [raw[i] for i in missing if raw[i] is not None]  # type: ignore[misc]
        # Use full universe for remaining
        all_present = [i for i, v in enumerate(raw) if v is not None]
        all_vals = [raw[i] for i in all_present]  # type: ignore[misc]
        w = winsorise(all_vals)
        z = zscore(w)
        uni = {all_present[j]: z[j] for j in range(len(all_present))}
        for i in missing:
            out[i] = uni.get(i)
    return out


def clip_loading(z: float, lo: float = -3.0, hi: float = 3.0) -> float:
    return max(lo, min(hi, z))
