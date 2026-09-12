"""Top-N selection from L4Opinion universe."""

from __future__ import annotations

from dataclasses import dataclass

from app.engines.e02.exposure import E02Exposure
from app.engines.e10.mapping import ELIGIBLE_LABELS, MIN_L4_SCORE, TOP_N_DEFAULT
from app.engines.l4.opinion import L4Opinion


@dataclass(frozen=True)
class Candidate:
    symbol: str
    score: float
    label: str
    confidence: float
    sector_id: str | None
    sigma: float
    l4_hash: str
    e02_hash: str | None


def select_top_n(
    opinions: dict[str, L4Opinion],
    exposures: dict[str, E02Exposure],
    *,
    top_n: int = TOP_N_DEFAULT,
    min_score: float = MIN_L4_SCORE,
    sigma_overrides: dict[str, float] | None = None,
) -> tuple[list[Candidate], list[dict[str, str]]]:
    """Select Top-N eligible L4 names. Rejects bearish / low-score / missing L4."""
    rejected: list[dict[str, str]] = []
    eligible: list[Candidate] = []
    overrides = sigma_overrides or {}

    for sym, op in opinions.items():
        symbol = sym.upper()
        if op.label not in ELIGIBLE_LABELS and op.composite_score < min_score:
            rejected.append({"symbol": symbol, "reason": "below_threshold"})
            continue
        if op.label in {"Bearish", "Strong Bearish"}:
            rejected.append({"symbol": symbol, "reason": "bearish_label"})
            continue
        exp = exposures.get(symbol)
        sector = exp.sector_id if exp else None
        sigma = overrides.get(symbol) or _sigma_from_e02(exp)
        eligible.append(
            Candidate(
                symbol=symbol,
                score=float(op.composite_score),
                label=op.label,
                confidence=float(op.confidence),
                sector_id=sector,
                sigma=sigma,
                l4_hash=op.hash,
                e02_hash=exp.hash if exp else None,
            )
        )

    eligible.sort(key=lambda c: (-c.score, c.symbol))
    selected = eligible[: max(0, top_n)]
    for c in eligible[top_n:]:
        rejected.append({"symbol": c.symbol, "reason": "outside_top_n"})
    return selected, rejected


def _sigma_from_e02(exp: E02Exposure | None) -> float:
    """Derive research vol proxy from E02 LowVol score (no MarketData)."""
    from app.engines.e10.mapping import DEFAULT_SIGMA, MAX_SIGMA, MIN_SIGMA

    if exp is None:
        return DEFAULT_SIGMA
    lowvol = exp.scores.get("F_LOWVOL")
    if lowvol is None:
        # Higher composite without lowvol → mild default
        return DEFAULT_SIGMA
    # High F_LOWVOL score ⇒ lower sigma
    # score 100 → ~MIN_SIGMA, score 0 → ~MAX_SIGMA
    sigma = MAX_SIGMA - (MAX_SIGMA - MIN_SIGMA) * (float(lowvol) / 100.0)
    return float(max(MIN_SIGMA, min(MAX_SIGMA, sigma)))
