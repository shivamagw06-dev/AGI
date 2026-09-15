"""Timeline engine — near / medium / long term catalyst windows."""

from __future__ import annotations

from typing import Any

from thesis_engine.schema import TIMELINE_HORIZONS

_HORIZON_WINDOW = {
    "Near Term": "0–6 months",
    "Medium Term": "6–24 months",
    "Long Term": "2–5 years",
}


def build_timeline(catalysts: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {h: [] for h in TIMELINE_HORIZONS}
    for c in catalysts:
        horizon = str(c.get("expected_timing") or "Medium Term")
        if horizon not in buckets:
            horizon = "Medium Term"
        buckets[horizon].append(
            {
                "id": c.get("id"),
                "event": c.get("event"),
                "polarity": c.get("polarity"),
                "probability": c.get("probability"),
                "pillar": c.get("pillar"),
                "evidence_required": c.get("evidence_required"),
            }
        )

    horizons = []
    for h in TIMELINE_HORIZONS:
        items = buckets[h]
        pos = sum(1 for i in items if i["polarity"] == "Positive")
        neg = sum(1 for i in items if i["polarity"] == "Negative")
        horizons.append(
            {
                "horizon": h,
                "window": _HORIZON_WINDOW[h],
                "catalyst_count": len(items),
                "positive": pos,
                "negative": neg,
                "skew": "Positive" if pos > neg else "Negative" if neg > pos else "Balanced",
                "catalysts": items[:6],
            }
        )

    return {
        "horizons": horizons,
        "next_review_trigger": (
            horizons[0]["catalysts"][0]["event"] if horizons[0]["catalysts"] else "Next quarterly disclosure"
        ),
        "monitoring_note": "Re-run belief update when any near-term catalyst resolves",
    }
