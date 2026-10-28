"""Deterministic scenario probability calculation — always sums to 100%."""

from __future__ import annotations

from typing import Any

from institutional_probability_confidence import traces
from institutional_probability_confidence.schema import ScenarioProbability


def calculate_probabilities(
    scenario_report: dict[str, Any],
    *,
    evidence_quality: dict[str, Any],
    analogue_count: int,
    triggers: list[dict[str, Any]],
) -> list[ScenarioProbability]:
    """Evidence-weighted institutional priors → normalised Bull/Base/Bear = 100%."""
    span = traces.begin(
        "probability_calculation",
        meta={"entity": scenario_report.get("entity"), "analogues": analogue_count},
    )

    # Institutional prior: Base is usually most likely
    weights = {"Bull": 24.0, "Base": 52.0, "Bear": 24.0}

    scenarios = {s.get("type"): s for s in (scenario_report.get("scenarios") or [])}
    pos_cats = 0
    neg_cats = 0
    for s in scenarios.values():
        for c in s.get("catalysts") or []:
            if c.get("polarity") == "positive":
                pos_cats += 1
            elif c.get("polarity") == "negative":
                neg_cats += 1

    # Catalyst tilt
    weights["Bull"] += min(10.0, pos_cats * 2.5)
    weights["Bear"] += min(10.0, neg_cats * 2.5)

    # Analogue slowdown / stress language tilts Bear; AI / easing language tilts Bull
    blob = str(scenario_report).lower()
    if any(tok in blob for tok in ("slowdown", "compression", "weak demand", "air-pocket")):
        weights["Bear"] += 4.0
        weights["Bull"] -= 1.0
    if any(tok in blob for tok in ("ai spending", "rate cut", "easing", "recovery")):
        weights["Bull"] += 3.0
        weights["Bear"] -= 0.5

    # More analogues → slightly less extreme (history supports multiple paths → Base)
    if analogue_count >= 2:
        weights["Base"] += 4.0
        weights["Bull"] -= 1.5
        weights["Bear"] -= 1.5

    # Contradictions concentrate mass on Base (institutional humility)
    contra_n = len(scenario_report.get("contradictions") or [])
    if contra_n:
        shift = min(8.0, contra_n * 2.0)
        weights["Base"] += shift
        weights["Bull"] -= shift / 2
        weights["Bear"] -= shift / 2

    # Trigger uncertainty (many Watching / Scheduled) → Base
    watching = sum(1 for t in triggers if str(t.get("status") or "").lower() in {"watching", "scheduled"})
    if watching >= 2:
        weights["Base"] += 3.0
        weights["Bull"] -= 1.5
        weights["Bear"] -= 1.5

    # Evidence quality: weak evidence → pull toward Base
    eq = float(evidence_quality.get("score_pct") or 70)
    if eq < 60:
        weights["Base"] += 6.0
        weights["Bull"] -= 3.0
        weights["Bear"] -= 3.0

    # Floor weights
    for k in weights:
        weights[k] = max(5.0, weights[k])

    total = sum(weights.values())
    raw = {k: (v / total) * 100.0 for k, v in weights.items()}

    # Integer allocation with Base absorbing rounding drift
    bull = int(round(raw["Bull"]))
    bear = int(round(raw["Bear"]))
    base = 100 - bull - bear
    if base < 5:
        # Rebalance if Base crushed
        deficit = 5 - base
        bull = max(5, bull - (deficit // 2 + deficit % 2))
        bear = max(5, bear - deficit // 2)
        base = 100 - bull - bear

    probs = {"Bull": bull, "Base": base, "Bear": bear}
    assert sum(probs.values()) == 100

    missing_n = len(((scenario_report.get("completeness") or {}).get("missing_evidence")) or [])
    out: list[ScenarioProbability] = []
    for name in ("Bull", "Base", "Bear"):
        s = scenarios.get(name) or {}
        ev_n = len(s.get("supporting_evidence") or [])
        level = "High" if ev_n >= 4 else "Medium" if ev_n >= 2 else "Low"
        out.append(
            ScenarioProbability(
                scenario=name,
                probability_pct=probs[name],
                supporting_evidence_level=level,
                historical_analogues=len(s.get("historical_analogues") or []),
                contradictions=contra_n if name != "Base" else max(0, contra_n - 1),
                missing_evidence=missing_n,
                drivers=s.get("drivers") or {},
                note="Deterministic evidence-weighted probability — not a price prediction",
            )
        )

    traces.end(span, output={"distribution": probs, "sum": 100})
    return out
