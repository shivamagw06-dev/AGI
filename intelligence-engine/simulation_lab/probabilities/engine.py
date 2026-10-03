"""Monte Carlo / probability distributions — seeded, reproducible, never deterministic."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any


def _seed_int(*parts: Any) -> int:
    raw = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def run_monte_carlo(
    *,
    run_key: str,
    assumptions: dict[str, Any],
    n: int = 2000,
    base_return: float = 0.08,
    base_vol: float = 0.16,
    shock: float = 0.0,
) -> dict[str, Any]:
    """Return a reproducible return distribution. Not a price path."""
    n = max(200, min(int(n), 10000))
    seed = _seed_int(run_key, sorted(assumptions.items()), n, base_return, base_vol, shock)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n):
        # Mixture: base gaussian + optional left-tail stress mass
        z = rng.gauss(0.0, 1.0)
        r = base_return + shock * 0.5 + base_vol * z
        if rng.random() < 0.08:
            r -= abs(rng.gauss(0.12 + abs(shock) * 0.2, 0.05))
        samples.append(r)
    samples.sort()
    def pct(p: float) -> float:
        idx = min(len(samples) - 1, max(0, int(p * (len(samples) - 1))))
        return round(samples[idx], 4)

    mean = sum(samples) / len(samples)
    var = sum((x - mean) ** 2 for x in samples) / len(samples)
    vol = math.sqrt(var)
    # Soft probability buckets (not buy/sell)
    bull = sum(1 for x in samples if x >= base_return + 0.05) / n
    base = sum(1 for x in samples if abs(x - base_return) < 0.05) / n
    bear = sum(1 for x in samples if x <= base_return - 0.05) / n
    stress = sum(1 for x in samples if x <= base_return - 0.15) / n
    total = bull + base + bear + stress
    if total <= 0:
        dist = {"bull": 0.2, "base": 0.4, "bear": 0.25, "stress": 0.15}
    else:
        dist = {
            "bull": round(bull / total, 3),
            "base": round(base / total, 3),
            "bear": round(bear / total, 3),
            "stress": round(stress / total, 3),
        }
    return {
        "n": n,
        "seed": seed,
        "reproducible": True,
        "distribution": dist,
        "bands": {
            "p05": pct(0.05),
            "p10": pct(0.10),
            "p50": pct(0.50),
            "p90": pct(0.90),
            "p95": pct(0.95),
        },
        "expected_return": round(mean, 4),
        "expected_volatility": round(vol, 4),
        "tail_risk_p05": pct(0.05),
        "max_drawdown_proxy": round(min(0.0, pct(0.05) - base_return), 4),
        "rule": "Probabilistic bands only — no unsupported deterministic outcomes",
        "not_a_price_prediction": True,
    }
