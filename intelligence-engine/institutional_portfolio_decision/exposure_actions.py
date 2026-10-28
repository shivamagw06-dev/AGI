"""Exposure actions — produce actions, not just measurements."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import ExposureRecord, InstitutionalPortfolio
from institutional_portfolio_decision.models import ExposureAction


def generate_exposure_actions(
    portfolio: InstitutionalPortfolio,
    *,
    target_sector_cap: float = 0.55,
    target_country_cap: float = 0.95,
) -> tuple[ExposureAction, ...]:
    actions: list[ExposureAction] = []
    exposures: Sequence[ExposureRecord] = portfolio.exposures

    sectors = [e for e in exposures if e.dimension == "sector"]
    for e in sectors:
        if e.weight >= target_sector_cap:
            to_w = round(max(0.35, target_sector_cap - 0.05), 4)
            actions.append(
                ExposureAction(
                    dimension="sector",
                    name=e.name,
                    from_weight=float(e.weight),
                    to_weight=to_w,
                    action="Reduce",
                    reason=f"Sector concentration {e.name} above institutional cap",
                )
            )
        elif e.weight <= 0.10 and len(sectors) == 1:
            actions.append(
                ExposureAction(
                    dimension="sector",
                    name=e.name,
                    from_weight=float(e.weight),
                    to_weight=float(e.weight),
                    action="Diversify",
                    reason="Single-sector book — increase diversification outside sector",
                )
            )

    countries = [e for e in exposures if e.dimension == "country"]
    for e in countries:
        if e.weight >= target_country_cap:
            actions.append(
                ExposureAction(
                    dimension="country",
                    name=e.name,
                    from_weight=float(e.weight),
                    to_weight=round(target_country_cap - 0.05, 4),
                    action="Reduce",
                    reason=f"Country exposure {e.name} nearly undiversified",
                )
            )

    recs = [e for e in exposures if e.dimension == "recommendation"]
    buy_w = sum(e.weight for e in recs if str(e.name).upper() == "BUY")
    sell_w = sum(e.weight for e in recs if str(e.name).upper() == "SELL")
    hold_w = sum(e.weight for e in recs if str(e.name).upper() == "HOLD")
    if sell_w >= 0.15:
        actions.append(
            ExposureAction(
                dimension="recommendation",
                name="SELL",
                from_weight=float(sell_w),
                to_weight=round(max(0.05, sell_w - 0.05), 4),
                action="Reduce",
                reason="Material SELL-referenced weight — reduce exposure",
            )
        )
    if hold_w >= 0.70 and buy_w < 0.10:
        actions.append(
            ExposureAction(
                dimension="style",
                name="HOLD-heavy",
                from_weight=float(hold_w),
                to_weight=float(hold_w),
                action="Maintain",
                reason="Portfolio posture is HOLD-dominant — maintain allocation bias",
            )
        )

    cash = float(portfolio.cash_weight or 0.0)
    if cash < 0.05 and (sectors and sectors[0].weight >= 0.70):
        actions.append(
            ExposureAction(
                dimension="liquidity",
                name="Cash",
                from_weight=cash,
                to_weight=round(min(0.12, cash + 0.04), 4),
                action="Increase",
                reason="Low cash with concentrated sector book",
            )
        )

    # Always emit at least a maintain signal when clean
    if not actions and sectors:
        top = sectors[0]
        actions.append(
            ExposureAction(
                dimension="sector",
                name=top.name,
                from_weight=float(top.weight),
                to_weight=float(top.weight),
                action="Maintain",
                reason="Exposures within institutional bands",
            )
        )

    return tuple(actions)
