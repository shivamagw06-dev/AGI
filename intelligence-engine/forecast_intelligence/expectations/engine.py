"""Expectation engine — market vs AGIB vs gap."""

from __future__ import annotations

from typing import Any


def expectation_gap(profile: dict[str, Any], probabilities: dict[str, Any]) -> dict[str, Any]:
    market = dict(profile.get("market_expects") or {})
    agib = dict(profile.get("agib_base") or {})
    diffs: list[dict[str, Any]] = []
    for key in sorted(set(market) | set(agib)):
        if key == "narrative":
            continue
        mv, av = market.get(key), agib.get(key)
        if isinstance(mv, (int, float)) and isinstance(av, (int, float)):
            diffs.append(
                {
                    "metric": key,
                    "market": mv,
                    "agib": av,
                    "difference": round(float(av) - float(mv), 3),
                    "direction": "agib_above" if av > mv else "agib_below" if av < mv else "inline",
                }
            )
        elif mv != av:
            diffs.append(
                {
                    "metric": key,
                    "market": mv,
                    "agib": av,
                    "difference": "qualitative",
                    "direction": "divergent",
                }
            )
    most = probabilities.get("most_likely")
    return {
        "market_expects": market,
        "agib_expects": {
            **agib,
            "most_likely_scenario": most,
            "most_likely_probability": probabilities.get("most_likely_probability"),
        },
        "difference": diffs,
        "narrative_gap": {
            "market": market.get("narrative"),
            "agib": agib.get("narrative"),
            "note": "Forecasts are relative to market expectations — never in isolation",
        },
        "rule": "Never forecast in isolation from market expectations",
    }
