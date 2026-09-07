"""Research-only shadow fusion for AIP weight experiments.

Mirrors L4 P0 vote logic with injectable weights.
Does NOT import or mutate production L4 fusion state.
"""

from __future__ import annotations

from typing import Any

from app.engines.l4.mapping import LABEL_THRESHOLDS, VOTER_WEIGHTS
from app.validation.models import ReplayDaySlice

# Simple sector map for golden / common Indian large caps (AIP-04 sector experiments).
SYMBOL_SECTOR: dict[str, str] = {
    "TCS": "Technology",
    "INFY": "Technology",
    "RELIANCE": "Energy",
    "HDFCBANK": "Financials",
    "SBIN": "Financials",
}


def label_from_score(score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Strong Bearish"


def _regime_signed(regime: str | None) -> float:
    if not regime:
        return 0.0
    r = regime.lower().replace("_", "").replace("-", "")
    if "riskon" in r or r in {"expansion", "bull"}:
        return 0.35
    if "riskoff" in r or r in {"contraction", "bear"}:
        return -0.35
    return 0.0


def _risk_signed(level: str | None) -> float:
    if not level:
        return 0.0
    l = level.lower()
    if l in {"low", "calm"}:
        return 0.15
    if l in {"elevated", "high", "severe"}:
        return -0.25
    return 0.0


def extract_signed_signals(
    day: ReplayDaySlice,
    symbol: str,
) -> dict[str, dict[str, float]]:
    """Build per-engine signed/confidence from replay slice (research approximation)."""
    e03 = day.e03_scores.get(symbol)
    e11 = day.e11_scores.get(symbol)
    conf = float(day.confidences.get(symbol, 0.55))
    return {
        "E03": {
            "signed": ((float(e03) - 50.0) / 50.0) if e03 is not None else 0.0,
            "confidence": max(0.05, conf if e03 is not None else 0.05),
            "present": 1.0 if e03 is not None else 0.0,
        },
        "E01": {
            "signed": _regime_signed(day.e01_regime),
            "confidence": 0.55 if day.e01_regime else 0.05,
            "present": 1.0 if day.e01_regime else 0.0,
        },
        "E14": {
            "signed": _risk_signed(day.e14_risk_level),
            "confidence": 0.55 if day.e14_risk_level else 0.05,
            "present": 1.0 if day.e14_risk_level else 0.0,
        },
        "E11": {
            "signed": ((float(e11) - 50.0) / 50.0) if e11 is not None else 0.0,
            "confidence": max(0.05, conf * 0.9 if e11 is not None else 0.05),
            "present": 1.0 if e11 is not None else 0.0,
        },
        "E02": {"signed": 0.0, "confidence": 0.05, "present": 0.0},
    }


def fuse_with_weights(
    signals: dict[str, dict[str, float]],
    weights: dict[str, float],
) -> dict[str, Any]:
    num = 0.0
    den = 0.0
    contributions: list[dict[str, Any]] = []
    for eng, w in weights.items():
        if w <= 0:
            continue
        sig = signals.get(eng) or {"signed": 0.0, "confidence": 0.05, "present": 0.0}
        if eng != "E02" and sig.get("present", 0.0) <= 0:
            continue
        if eng == "E02":
            continue
        x = float(sig["signed"])
        c = max(0.05, float(sig["confidence"]))
        effective = float(w) * c
        num += effective * x
        den += effective
        contributions.append(
            {
                "engine": eng,
                "weight": float(w),
                "confidence": round(c, 4),
                "signed": round(x, 4),
                "contribution": round(effective * x, 4),
            }
        )
    blended = (num / den) if den > 0 else 0.0
    score = round(50.0 + 50.0 * max(-1.0, min(1.0, blended)), 1)
    label = label_from_score(score)
    conf = round(min(0.95, max(0.05, den / (den + 0.5))), 4) if den > 0 else 0.05
    shares = {
        c["engine"]: abs(float(c["contribution"])) for c in contributions
    }
    total = sum(shares.values()) or 1.0
    engine_shares = {k: round(v / total, 4) for k, v in shares.items()}
    dominant = max(engine_shares, key=engine_shares.get) if engine_shares else None
    return {
        "score": score,
        "label": label,
        "confidence": conf,
        "contributions": contributions,
        "engine_shares": engine_shares,
        "dominant_engine": dominant,
    }


def score_universe(
    days: list[ReplayDaySlice],
    weights: dict[str, float],
    *,
    regime_filter: str | None = None,
    sector_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Score each symbol/day under candidate weights (shadow)."""
    rows: list[dict[str, Any]] = []
    for day in days:
        if regime_filter and (day.e01_regime or "") != regime_filter:
            # Still score, but tag filter miss — keep observations for fairness
            pass
        for sym in day.l4_scores.keys() or day.e03_scores.keys():
            if sector_filter and SYMBOL_SECTOR.get(sym) != sector_filter:
                continue
            signals = extract_signed_signals(day, sym)
            fused = fuse_with_weights(signals, weights)
            rows.append(
                {
                    "as_of": day.as_of,
                    "symbol": sym,
                    "score": fused["score"],
                    "label": fused["label"],
                    "confidence": fused["confidence"],
                    "engine_shares": fused["engine_shares"],
                    "dominant_engine": fused["dominant_engine"],
                    "contributions": fused["contributions"],
                    "sector": SYMBOL_SECTOR.get(sym),
                    "regime": day.e01_regime,
                }
            )
    return rows


def baseline_weights() -> dict[str, float]:
    return {k: float(v) for k, v in VOTER_WEIGHTS.items()}
