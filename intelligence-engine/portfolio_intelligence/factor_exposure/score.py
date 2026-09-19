"""Factor exposure — quality/value/growth/momentum/etc. portfolio tilt."""

from __future__ import annotations

from typing import Any

FACTORS = (
    "quality",
    "value",
    "growth",
    "momentum",
    "low_vol",
    "dividend",
    "leverage",
    "profitability",
    "large_cap",
    "mid_cap",
    "small_cap",
)


def factor_exposure(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    total_w = sum(float(h.get("weight") or 0) for h in holdings) or 1.0
    agg = {f: 0.0 for f in FACTORS}
    for h in holdings:
        w = float(h.get("weight") or 0) / total_w
        factors = h.get("factors") if isinstance(h.get("factors"), dict) else {}
        for f in ("quality", "value", "growth", "momentum", "low_vol", "dividend", "leverage", "profitability"):
            agg[f] += w * float(factors.get(f) or 0.5)
        mcap = str(h.get("market_cap") or "large").lower()
        if mcap == "large":
            agg["large_cap"] += w
        elif mcap == "mid":
            agg["mid_cap"] += w
        else:
            agg["small_cap"] += w

    # Balance score: prefer quality/profitability without extreme single-factor bets
    balance = 70.0
    if agg["quality"] >= 0.7:
        balance += 10
    if agg["growth"] > 0.75 and agg["quality"] < 0.55:
        balance -= 15
    if agg["leverage"] > 0.6:
        balance -= 10
    balance = max(0.0, min(100.0, balance))

    return {
        "factors": {k: round(v, 3) for k, v in agg.items()},
        "factor_balance": round(balance, 1),
        "dominant": max(
            ((k, v) for k, v in agg.items() if k not in {"large_cap", "mid_cap", "small_cap"}),
            key=lambda kv: kv[1],
        )[0],
    }
