"""PCE-01 constraint evaluation — deterministic Pass / Warning / Violation."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from institutional_portfolio.portfolio_entities import InstitutionalPortfolio
from institutional_policy.models import ConstraintResult, MandateProfile, PolicyConstraint

# Near-limit band: within 10% of the limit on the breach side for max, or within 10% headroom for min
_NEAR_RATIO = 0.10


def _sector_weight(portfolio: InstitutionalPortfolio, aliases: Sequence[str]) -> float:
    aliases_l = {a.lower() for a in aliases}
    for e in portfolio.exposures:
        if e.dimension == "sector" and (e.name or "").strip().lower() in aliases_l:
            return float(e.weight)
    # Fall back to holdings rollup
    total = 0.0
    for h in portfolio.holdings:
        if (h.sector or "").strip().lower() in aliases_l:
            total += float(h.weight or 0.0)
    return total


def _measure_actual(
    constraint: PolicyConstraint,
    portfolio: InstitutionalPortfolio,
    risk: Any = None,
) -> tuple[float, str, str, float, float]:
    """
    Return (actual, detail, action_ticker, from_value, to_value).

    from/to are suggestion anchors when violated (else 0).
    """
    cid = constraint.constraint_id
    holdings = sorted(portfolio.holdings, key=lambda h: float(h.weight or 0.0), reverse=True)
    largest = holdings[0] if holdings else None
    cash = float(portfolio.cash_weight or 0.0)

    hhi = 0.0
    top5 = 0.0
    sector_conc = 0.0
    illiquid = 0.0
    exit_days = 0.0
    stress_loss = 0.0  # positive magnitude of worst loss
    beta = 1.0
    if risk is not None:
        conc = getattr(risk, "concentration", None)
        if conc is not None:
            hhi = float(getattr(conc, "hhi", 0.0) or 0.0)
            top5 = float(getattr(conc, "top_5_weight", 0.0) or 0.0)
            sector_conc = float(getattr(conc, "sector_concentration", 0.0) or 0.0)
        liq = getattr(risk, "liquidity", None)
        if liq is not None:
            illiquid = float(getattr(liq, "illiquid_weight", 0.0) or 0.0)
            exit_days = float(getattr(liq, "average_exit_days", 0.0) or 0.0)
        beta = float(getattr(risk, "market_beta", 1.0) or 1.0)
        stresses = getattr(risk, "stress_results", ()) or ()
        if stresses:
            worst = min(stresses, key=lambda s: float(s.portfolio_impact_pct))
            stress_loss = abs(min(0.0, float(worst.portfolio_impact_pct)))
    else:
        weights = [float(h.weight or 0.0) for h in holdings]
        hhi = sum(w * w for w in weights)
        top5 = sum(weights[:5])
        sectors = [e for e in portfolio.exposures if e.dimension == "sector"]
        sector_conc = float(sectors[0].weight) if sectors else 0.0

    ticker = largest.ticker if largest else ""
    largest_w = float(largest.weight) if largest else 0.0

    if cid == "pos_max_holding":
        return (
            largest_w,
            f"Largest holding {ticker or '—'} at {largest_w:.0%}",
            ticker,
            largest_w,
            float(constraint.limit),
        )
    if cid == "pos_max_top5":
        return top5, f"Top-5 weight {top5:.0%}", "", top5, float(constraint.limit)
    if cid == "sec_max_financials":
        w = _sector_weight(portfolio, ("banking", "banks", "financials", "finance"))
        return w, f"Financials / Banking weight {w:.0%}", "", w, float(constraint.limit)
    if cid == "sec_max_it":
        w = _sector_weight(portfolio, ("technology", "information technology", "it"))
        return w, f"IT weight {w:.0%}", "", w, float(constraint.limit)
    if cid == "sec_max_energy":
        w = _sector_weight(portfolio, ("energy", "oil & gas", "oil and gas"))
        return w, f"Energy weight {w:.0%}", "", w, float(constraint.limit)
    if cid == "cash_min":
        return cash, f"Cash weight {cash:.0%}", "CASH", cash, float(constraint.limit)
    if cid == "cash_max":
        return cash, f"Cash weight {cash:.0%}", "CASH", cash, float(constraint.limit)
    if cid == "div_min_holdings":
        n = float(len(holdings))
        return n, f"{int(n)} holdings", "", n, float(constraint.limit)
    if cid == "div_max_hhi":
        return hhi, f"HHI={hhi:.3f}", "", hhi, float(constraint.limit)
    if cid == "div_max_sector":
        return (
            sector_conc,
            f"Top sector concentration {sector_conc:.0%}",
            "",
            sector_conc,
            float(constraint.limit),
        )
    if cid == "liq_max_illiquid":
        return illiquid, f"Illiquid weight {illiquid:.0%}", "", illiquid, float(constraint.limit)
    if cid == "liq_max_exit_days":
        return (
            exit_days,
            f"Average exit days {exit_days:.2f}",
            "",
            exit_days,
            float(constraint.limit),
        )
    if cid == "risk_max_stress":
        return (
            stress_loss,
            f"Worst stress loss {stress_loss:.1f}%",
            "",
            stress_loss,
            float(constraint.limit),
        )
    if cid == "risk_max_beta":
        return beta, f"Portfolio beta {beta:.2f}", "", beta, float(constraint.limit)

    return 0.0, f"Unknown constraint {cid}", "", 0.0, 0.0


def _status(operator: str, actual: float, limit: float) -> tuple[str, float]:
    if operator == "max":
        headroom = float(limit) - float(actual)
        if actual > limit + 1e-12:
            return "Violation", headroom
        if limit > 0 and headroom <= abs(limit) * _NEAR_RATIO:
            return "Warning", headroom
        return "Pass", headroom
    # min
    headroom = float(actual) - float(limit)
    if actual + 1e-12 < limit:
        return "Violation", headroom
    if limit > 0 and headroom <= abs(limit) * _NEAR_RATIO:
        return "Warning", headroom
    return "Pass", headroom


def _action_text(constraint: PolicyConstraint, result_status: str, ticker: str, actual: float, limit: float) -> str:
    if result_status != "Violation":
        return ""
    if constraint.constraint_id == "pos_max_holding" and ticker:
        return f"Reduce {ticker} {actual:.0%} → {limit:.0%}"
    if constraint.constraint_id == "cash_min":
        return f"Increase Cash {actual:.0%} → {limit:.0%}"
    if constraint.constraint_id == "cash_max":
        return f"Reduce Cash {actual:.0%} → {limit:.0%}"
    if constraint.category == "sector":
        return f"Reduce {constraint.name} {actual:.0%} → {limit:.0%}"
    if constraint.constraint_id == "div_min_holdings":
        return f"Add holdings to reach {int(limit)} names (now {int(actual)})"
    if constraint.constraint_id == "div_max_hhi":
        return f"Diversify to bring HHI below {limit:.2f} (now {actual:.2f})"
    if constraint.constraint_id == "div_max_sector":
        return f"Reduce sector concentration {actual:.0%} → {limit:.0%}"
    if constraint.constraint_id == "liq_max_illiquid":
        return f"Cut illiquid exposure {actual:.0%} → {limit:.0%}"
    if constraint.constraint_id == "liq_max_exit_days":
        return f"Improve exit capacity below {limit:.1f} days (now {actual:.1f})"
    if constraint.constraint_id == "risk_max_stress":
        return f"Reduce stress loss below {limit:.1f}% (now {actual:.1f}%)"
    if constraint.constraint_id == "risk_max_beta":
        return f"Lower beta below {limit:.2f} (now {actual:.2f})"
    return f"Bring {constraint.name} within {constraint.operator} {limit}"


def evaluate_constraint(
    constraint: PolicyConstraint,
    portfolio: InstitutionalPortfolio,
    risk: Any = None,
) -> ConstraintResult:
    actual, detail, ticker, from_v, to_v = _measure_actual(constraint, portfolio, risk)
    status, headroom = _status(constraint.operator, actual, float(constraint.limit))
    action = _action_text(constraint, status, ticker, actual, float(constraint.limit))
    return ConstraintResult(
        constraint_id=constraint.constraint_id,
        category=constraint.category,
        name=constraint.name,
        operator=constraint.operator,
        limit=float(constraint.limit),
        actual=round(float(actual), 6),
        status=status,
        headroom=round(float(headroom), 6),
        detail=detail,
        action=action,
        action_ticker=ticker if status == "Violation" else "",
        from_value=round(float(from_v), 6) if status == "Violation" else 0.0,
        to_value=round(float(to_v), 6) if status == "Violation" else 0.0,
    )


def evaluate_all_constraints(
    mandate: MandateProfile,
    portfolio: InstitutionalPortfolio,
    risk: Any = None,
) -> tuple[ConstraintResult, ...]:
    return tuple(evaluate_constraint(c, portfolio, risk) for c in mandate.constraints)
