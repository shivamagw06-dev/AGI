"""Deterministic allocation actions — never mutates company decisions."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord, InstitutionalPortfolio
from institutional_portfolio_decision.models import AllocationAction, CompanyDecisionRef


def _clamp(weight: float) -> float:
    return round(max(0.0, min(0.40, float(weight))), 4)


def generate_allocation_actions(
    portfolio: InstitutionalPortfolio,
    *,
    refs: Sequence[CompanyDecisionRef],
    sector_concentration: float,
    hhi: float,
) -> tuple[AllocationAction, ...]:
    """
    Produce sizing intents from company decision *references* + concentration.

    Rules (deterministic, no optimiser):
    - BUY + high confidence + weight < 20% → modest increase
    - SELL / REDUCE-like → decrease
    - Largest holding when HHI high or sector concentrated → trim
    - HOLD with elevated single-name weight → slight trim toward 20%
    """
    by_ticker = {r.ticker: r for r in refs}
    holds = sorted(portfolio.holdings, key=lambda h: h.weight, reverse=True)
    actions: list[AllocationAction] = []

    for h in holds:
        ref = by_ticker.get(h.ticker)
        rec = (ref.recommendation if ref else h.recommendation or "HOLD").upper()
        conf = int(ref.confidence if ref else h.confidence or 0)
        decision_id = ref.decision_id if ref else h.decision_id
        from_w = float(h.weight)
        to_w = from_w
        reason = ""

        if rec == "BUY" and conf >= 80 and from_w < 0.20:
            to_w = _clamp(from_w + 0.02)
            reason = "Improved conviction (BUY reference)"
        elif rec == "SELL":
            to_w = _clamp(max(0.0, from_w - 0.03))
            reason = "Company decision reference is SELL"
        elif (hhi >= 0.20 or sector_concentration >= 0.70) and from_w >= 0.25:
            to_w = _clamp(from_w - 0.03)
            reason = "Reduce single-name concentration"
        elif from_w >= 0.28 and rec in {"HOLD", "SELL"}:
            to_w = _clamp(0.25)
            reason = "Trim oversized HOLD position"

        if abs(to_w - from_w) >= 0.005:
            actions.append(
                AllocationAction(
                    ticker=h.ticker,
                    from_weight=from_w,
                    to_weight=to_w,
                    reason=reason,
                    company_decision_id=decision_id,
                    company_recommendation=rec,
                )
            )

    # Cash action when concentration/risk elevated and cash low
    cash = float(portfolio.cash_weight or 0.0)
    if (hhi >= 0.22 or sector_concentration >= 0.80) and cash < 0.12:
        # Represented as synthetic CASH ticker for CLI/UI clarity
        actions.append(
            AllocationAction(
                ticker="CASH",
                from_weight=cash,
                to_weight=round(min(0.15, cash + 0.04), 4),
                reason="Macro / concentration buffer — increase cash",
                company_decision_id="",
                company_recommendation="",
            )
        )

    actions.sort(key=lambda a: abs(a.to_weight - a.from_weight), reverse=True)
    return tuple(actions)
