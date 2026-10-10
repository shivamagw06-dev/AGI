"""Monitoring plan for InstitutionalPortfolioDecision."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import InstitutionalPortfolio
from institutional_portfolio_decision.models import (
    AllocationAction,
    CompanyDecisionRef,
    MonitoringPlan,
)


def build_monitoring_plan(
    portfolio: InstitutionalPortfolio,
    *,
    refs: Sequence[CompanyDecisionRef],
    allocation_actions: Sequence[AllocationAction],
    recommendation: str,
    sector_concentration: float,
) -> MonitoringPlan:
    high: list[str] = []
    reviews: list[str] = []
    earnings: list[str] = []
    obs_watch: list[str] = []
    scenarios: list[str] = []
    committee: list[str] = []

    for h in sorted(portfolio.holdings, key=lambda x: x.weight, reverse=True):
        if h.weight >= 0.20:
            high.append(h.ticker)
        earnings.append(f"{h.ticker} quarterly results")
        obs_watch.append(h.ticker)

    for r in refs:
        if r.recommendation in {"SELL", "BUY"} and r.confidence >= 80:
            reviews.append(f"{r.ticker} company decision {r.recommendation}")
        if r.recommendation == "SELL":
            high.append(r.ticker)

    for a in allocation_actions:
        if a.ticker != "CASH" and abs(a.to_weight - a.from_weight) >= 0.02:
            reviews.append(f"{a.ticker} allocation {a.from_weight:.0%}→{a.to_weight:.0%}")

    if sector_concentration >= 0.70:
        scenarios.append("Sector stress — dominant sector drawdown")
        committee.append("Review sector concentration vs mandate")
    if recommendation in {"Reduce Concentration", "Increase Diversification", "Increase Cash"}:
        committee.append(f"Committee review: {recommendation}")
    if recommendation == "Review Portfolio":
        committee.append("Full portfolio review required")

    # Deduplicate preserve order
    def _uniq(items: list[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        out: list[str] = []
        for i in items:
            if i and i not in seen:
                seen.add(i)
                out.append(i)
        return tuple(out)

    return MonitoringPlan(
        high_priority_holdings=_uniq(high),
        required_reviews=_uniq(reviews),
        upcoming_earnings=_uniq(earnings)[:8],
        observation_watch=_uniq(obs_watch),
        scenario_reruns=_uniq(scenarios),
        committee_items=_uniq(committee),
    )


def monitoring_items_flat(plan: MonitoringPlan) -> tuple[str, ...]:
    items: list[str] = []
    for t in plan.high_priority_holdings:
        items.append(f"High priority: {t}")
    for t in plan.required_reviews:
        items.append(f"Review: {t}")
    for t in plan.committee_items:
        items.append(f"Committee: {t}")
    return tuple(items)
