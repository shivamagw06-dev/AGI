"""Diversification score — Herfindahl-style + sector breadth."""

from __future__ import annotations

from typing import Any


def diversification_score(holdings: list[dict[str, Any]], *, cash_weight: float) -> dict[str, Any]:
    weights = [float(h.get("weight") or 0) for h in holdings if float(h.get("weight") or 0) > 0]
    if cash_weight:
        weights.append(float(cash_weight))
    hhi = sum(w * w for w in weights) if weights else 1.0
    # Lower HHI → better diversification. Equal 10 names ≈ 0.1
    score = max(0.0, min(100.0, (1.0 - hhi) / 0.9 * 100.0))
    sectors = {h.get("sector") for h in holdings}
    if len(sectors) >= 5:
        score = min(100.0, score + 5)
    elif len(sectors) <= 2:
        score = max(0.0, score - 15)
    return {
        "diversification": round(score, 1),
        "hhi": round(hhi, 4),
        "n_holdings": len(holdings),
        "n_sectors": len(sectors),
        "label": "strong" if score >= 70 else "adequate" if score >= 50 else "weak",
    }
