"""Guidance accuracy engine + Management Guidance Score 0–100."""

from __future__ import annotations

from typing import Any


def guidance_score(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "guidance_score": 50.0,
            "historical_accuracy": 50.0,
            "optimism_bias": 50.0,
            "conservatism": 50.0,
            "forecast_reliability": 50.0,
            "consistency": 50.0,
            "n": 0,
        }
    resolved = [e for e in events if e.get("outcome") in {"delivered", "missed", "partially_delivered"}]
    n = len(resolved) or 1
    delivered = sum(1 for e in resolved if e.get("outcome") == "delivered")
    partial = sum(1 for e in resolved if e.get("outcome") == "partially_delivered")
    missed = sum(1 for e in resolved if e.get("outcome") == "missed")
    historical_accuracy = 100.0 * (delivered + 0.5 * partial) / n

    # optimism: maintained/raised then missed
    opt_hits = [
        e for e in resolved
        if e.get("status") in {"maintained", "raised"} and e.get("outcome") == "missed"
    ]
    optimism_bias = min(100.0, 40.0 + 20.0 * len(opt_hits))  # higher = more optimistic/biased
    conservatism = max(0.0, 100.0 - optimism_bias)

    statuses = [e.get("status") for e in events]
    withdrawn = sum(1 for s in statuses if s == "withdrawn")
    consistency = max(0.0, 100.0 - 15.0 * withdrawn - 5.0 * sum(1 for s in statuses if s == "lowered"))
    forecast_reliability = round(0.6 * historical_accuracy + 0.4 * consistency, 1)

    # score penalizes optimism bias
    score = round(
        historical_accuracy * 0.45
        + forecast_reliability * 0.25
        + (100.0 - optimism_bias) * 0.15
        + consistency * 0.15,
        1,
    )
    return {
        "guidance_score": score,
        "historical_accuracy": round(historical_accuracy, 1),
        "optimism_bias": round(optimism_bias, 1),
        "conservatism": round(conservatism, 1),
        "forecast_reliability": forecast_reliability,
        "consistency": round(consistency, 1),
        "counts": {"delivered": delivered, "partial": partial, "missed": missed, "pending": len(events) - len(resolved)},
        "n": len(events),
        "events": events,
    }
