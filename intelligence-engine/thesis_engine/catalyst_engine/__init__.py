"""Catalyst engine — positive / negative / neutral catalysts with timing and probability."""

from __future__ import annotations

from typing import Any

# Catalyst templates by pillar
_CATALYSTS: dict[str, list[dict[str, Any]]] = {
    "Business Quality": [
        {"polarity": "Positive", "event": "Deposit / franchise acceleration", "timing": "Near Term", "evidence": ["FIL", "Quarterly disclosures"], "probability": 0.45},
        {"polarity": "Negative", "event": "Deposit or franchise pressure intensifies", "timing": "Near Term", "evidence": ["FIL", "Transcript"], "probability": 0.4},
        {"polarity": "Neutral", "event": "Distribution expansion with unchanged mix", "timing": "Medium Term", "evidence": ["Business"], "probability": 0.35},
    ],
    "Financial Quality": [
        {"polarity": "Positive", "event": "Lower funding cost flows through to margins", "timing": "Near Term", "evidence": ["FIL", "Macro"], "probability": 0.42},
        {"polarity": "Negative", "event": "Higher credit costs in unsecured book", "timing": "Medium Term", "evidence": ["FIL", "Risk"], "probability": 0.38},
        {"polarity": "Neutral", "event": "Stable asset quality with mix shift", "timing": "Medium Term", "evidence": ["FIL"], "probability": 0.4},
    ],
    "Competitive Position": [
        {"polarity": "Negative", "event": "Peer share gains narrow historical advantage", "timing": "Medium Term", "evidence": ["PIL"], "probability": 0.44},
        {"polarity": "Positive", "event": "Competitive discipline restores pricing power", "timing": "Long Term", "evidence": ["PIL", "Industry"], "probability": 0.3},
    ],
    "Valuation": [
        {"polarity": "Positive", "event": "Re-rating as earnings visibility improves", "timing": "Medium Term", "evidence": ["PIL", "Forecast"], "probability": 0.35},
        {"polarity": "Negative", "event": "Multiple mean-reversion toward historical median", "timing": "Medium Term", "evidence": ["Historical", "PIL"], "probability": 0.42},
    ],
    "Macro Alignment": [
        {"polarity": "Positive", "event": "Credit demand recovery on policy easing", "timing": "Near Term", "evidence": ["Macro"], "probability": 0.43},
        {"polarity": "Negative", "event": "Regulatory tightening or liquidity squeeze", "timing": "Near Term", "evidence": ["Macro", "Risk"], "probability": 0.33},
    ],
    "Capital Allocation": [
        {"polarity": "Positive", "event": "Improved incremental ROIC on new capital", "timing": "Long Term", "evidence": ["FIL", "Management"], "probability": 0.32},
        {"polarity": "Negative", "event": "Dilutive capital raise or value-destructive M&A", "timing": "Medium Term", "evidence": ["Management", "FIL"], "probability": 0.25},
    ],
    "Portfolio Fit": [
        {"polarity": "Neutral", "event": "Factor exposure rebalancing changes sizing", "timing": "Near Term", "evidence": ["Portfolio"], "probability": 0.4},
        {"polarity": "Negative", "event": "Correlation spike reduces diversification benefit", "timing": "Medium Term", "evidence": ["Portfolio", "Risk"], "probability": 0.3},
    ],
}


def build_catalysts(pillars: list[dict[str, Any]], entity: str = "the subject") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    idx = 1
    for p in pillars:
        templates = _CATALYSTS.get(p["pillar"]) or []
        for t in templates:
            strength = float(p.get("strength") or 0.5)
            # Positive catalysts more likely when pillar is strong; negative when weak
            adj = 0.0
            if t["polarity"] == "Positive":
                adj = (strength - 0.5) * 0.25
            elif t["polarity"] == "Negative":
                adj = (0.5 - strength) * 0.25
            probability = round(max(0.05, min(0.9, float(t["probability"]) + adj)), 4)
            out.append(
                {
                    "id": f"CAT-{idx:03d}",
                    "polarity": t["polarity"],
                    "event": f"{t['event']} at {entity}",
                    "pillar": p["pillar"],
                    "expected_timing": t["timing"],
                    "evidence_required": list(t["evidence"]),
                    "probability": probability,
                    "probability_pct": round(probability * 100),
                    "impact": "High" if probability >= 0.45 else "Moderate" if probability >= 0.3 else "Low",
                }
            )
            idx += 1
    out.sort(key=lambda c: -float(c["probability"]))
    return out


def catalyst_summary(catalysts: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for c in catalysts:
        counts[str(c.get("polarity") or "Neutral")] = counts.get(str(c.get("polarity") or "Neutral"), 0) + 1
    return {
        "total": len(catalysts),
        "by_polarity": counts,
        "top_positive": [c for c in catalysts if c["polarity"] == "Positive"][:3],
        "top_negative": [c for c in catalysts if c["polarity"] == "Negative"][:3],
        "net_skew": round(
            (counts.get("Positive", 0) - counts.get("Negative", 0)) / max(len(catalysts), 1), 4
        ),
    }
