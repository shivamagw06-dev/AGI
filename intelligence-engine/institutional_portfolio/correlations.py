"""Deterministic portfolio correlation proxies — no ML / no market covariance matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord


@dataclass(frozen=True)
class CorrelationEdge:
    ticker_a: str
    ticker_b: str
    score: float
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker_a": self.ticker_a,
            "ticker_b": self.ticker_b,
            "score": float(self.score),
            "basis": self.basis,
            "llm": False,
            "estimated": True,
        }


def estimate_pairwise_correlation(a: HoldingRecord, b: HoldingRecord) -> CorrelationEdge:
    """
    Institutional proxy correlation from shared structure.

    Same sector + industry → high; same sector → medium; same country → modest;
    otherwise low. Deterministic — not a statistical estimator.
    """
    score = 0.15
    basis_parts: list[str] = []
    if a.country and a.country == b.country:
        score += 0.15
        basis_parts.append("country")
    if a.sector and a.sector == b.sector:
        score += 0.35
        basis_parts.append("sector")
    if a.industry and a.industry == b.industry:
        score += 0.25
        basis_parts.append("industry")
    if a.recommendation and a.recommendation == b.recommendation:
        score += 0.05
        basis_parts.append("recommendation")
    score = min(0.95, max(0.05, score))
    return CorrelationEdge(
        ticker_a=a.ticker,
        ticker_b=b.ticker,
        score=round(score, 4),
        basis="+".join(basis_parts) or "residual",
    )


def compute_correlations(holdings: Sequence[HoldingRecord]) -> tuple[CorrelationEdge, ...]:
    rows: list[CorrelationEdge] = []
    ordered = sorted(holdings, key=lambda h: h.ticker)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1 :]:
            rows.append(estimate_pairwise_correlation(a, b))
    rows.sort(key=lambda c: c.score, reverse=True)
    return tuple(rows)


def average_correlation(edges: Sequence[CorrelationEdge]) -> float | None:
    if not edges:
        return None
    return round(sum(e.score for e in edges) / len(edges), 4)
