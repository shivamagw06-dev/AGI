"""Cash Flow Statement Reconstruction — given ONLY an Income Statement and
Balance Sheet (no Cash Flow Statement), rebuild Operating / Investing /
Financing Cash Flow from first principles, then reconcile against the
actual cash movement.

This is a genuine accounting-reconstruction exercise (Institutional
Accounting Exam, Section G), not a lookup: every line is derived from
Balance Sheet deltas and the retained-earnings bridge, exactly the way
an analyst would when only two statements are available.

Operating CF  = PAT + Depreciation ± working-capital deltas
Investing CF  = −Capex (inferred: ΔNet PPE + Depreciation) − Δ(Goodwill + Intangibles)
Financing CF  = Δ Total Debt + Δ Share Capital − Δ Treasury Stock − Dividends
                (Dividends inferred from the retained-earnings bridge:
                 Dividends = PAT − ΔRetained Earnings)

The reconstructed Net Change in Cash is compared against the ACTUAL
change in the Cash account. Any gap is reported honestly as an
"unexplained residual" rather than silently forced to zero — a real
reconstruction from only two statements cannot always perfectly explain
every cash movement (e.g. FX translation, non-cash equity adjustments),
and pretending otherwise would itself be a form of fabrication.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from financial_statement_intelligence.schema import StatementPeriod

_RESIDUAL_TOLERANCE = 1e-6


@dataclass
class ReconstructionLine:
    key: str
    label: str
    value: float
    derivation: str


def _wc_asset_delta(prior: StatementPeriod, current: StatementPeriod) -> list[ReconstructionLine]:
    lines = []
    for field, label in (
        ("receivables", "Receivables"),
        ("inventory", "Inventory"),
        ("other_current_assets", "Other Current Assets"),
    ):
        delta = getattr(current, field) - getattr(prior, field)
        if abs(delta) > 1e-9:
            lines.append(
                ReconstructionLine(
                    field, f"{'Increase' if delta > 0 else 'Decrease'} in {label}", -delta,
                    f"{label} moved {getattr(prior, field):,.0f} → {getattr(current, field):,.0f}; "
                    f"an increase in an operating asset consumes cash (−), a decrease releases cash (+).",
                )
            )
    return lines


def _wc_liability_delta(prior: StatementPeriod, current: StatementPeriod) -> list[ReconstructionLine]:
    lines = []
    for field, label in (
        ("payables", "Payables"),
        ("other_current_liabilities", "Other Current Liabilities"),
        ("deferred_tax_liability", "Deferred Tax Liability"),
    ):
        delta = getattr(current, field) - getattr(prior, field)
        if abs(delta) > 1e-9:
            lines.append(
                ReconstructionLine(
                    field, f"{'Increase' if delta > 0 else 'Decrease'} in {label}", delta,
                    f"{label} moved {getattr(prior, field):,.0f} → {getattr(current, field):,.0f}; "
                    f"an increase in an operating liability conserves cash (+), a decrease uses cash (−).",
                )
            )
    return lines


def _reconstruct_operating(prior: StatementPeriod, current: StatementPeriod) -> dict[str, Any]:
    lines: list[ReconstructionLine] = [
        ReconstructionLine("pat", "Profit After Tax (starting point)", current.pat,
                            "The indirect method always starts from PAT — the accounting measure of profit."),
        ReconstructionLine("depreciation", "Depreciation (non-cash add-back)", current.depreciation,
                            "Depreciation reduced PAT but never touched Cash — add it back."),
    ]
    lines.extend(_wc_asset_delta(prior, current))
    lines.extend(_wc_liability_delta(prior, current))
    total = round(sum(l.value for l in lines), 2)
    return {"total": total, "lines": [l.__dict__ for l in lines]}


def _reconstruct_investing(prior: StatementPeriod, current: StatementPeriod) -> dict[str, Any]:
    implied_capex = (current.ppe_net - prior.ppe_net) + current.depreciation
    lines: list[ReconstructionLine] = [
        ReconstructionLine(
            "implied_capex", "Implied Capex (from ΔNet PPE + Depreciation)", -implied_capex,
            f"Net PPE moved {prior.ppe_net:,.0f} → {current.ppe_net:,.0f}; adding back this period's "
            f"Depreciation ({current.depreciation:,.0f}) recovers the gross cash spent on new assets, "
            f"assuming no disposals — Capex ≈ ΔNet PPE + Depreciation.",
        )
    ]
    acquisition_spend = (current.goodwill - prior.goodwill) + (current.intangibles - prior.intangibles)
    if abs(acquisition_spend) > 1e-9:
        lines.append(
            ReconstructionLine(
                "acquisition_spend", "Implied Acquisition/Intangible Spend", -acquisition_spend,
                f"Goodwill + Intangibles moved by {acquisition_spend:,.0f} — likely acquisition or "
                f"capitalised-intangible spend, inferred purely from the balance sheet (no CF given).",
            )
        )
    total = round(sum(l.value for l in lines), 2)
    return {"total": total, "lines": [l.__dict__ for l in lines], "implied_capex": round(implied_capex, 2)}


def _reconstruct_financing(prior: StatementPeriod, current: StatementPeriod) -> dict[str, Any]:
    debt_delta = current.total_debt - prior.total_debt
    equity_delta = current.share_capital - prior.share_capital
    treasury_delta = current.treasury_stock - prior.treasury_stock
    implied_dividends = current.pat - (current.retained_earnings - prior.retained_earnings)

    lines: list[ReconstructionLine] = []
    if abs(debt_delta) > 1e-9:
        lines.append(
            ReconstructionLine("debt_delta", "Net Debt Raised / (Repaid)", debt_delta,
                                f"Total Debt moved {prior.total_debt:,.0f} → {current.total_debt:,.0f}.")
        )
    if abs(equity_delta) > 1e-9:
        lines.append(
            ReconstructionLine("equity_delta", "New Share Capital Raised", equity_delta,
                                f"Share Capital moved {prior.share_capital:,.0f} → {current.share_capital:,.0f}.")
        )
    if abs(treasury_delta) > 1e-9:
        lines.append(
            ReconstructionLine("treasury_delta", "Implied Buybacks (ΔTreasury Stock)", -treasury_delta,
                                f"Treasury Stock moved {prior.treasury_stock:,.0f} → {current.treasury_stock:,.0f} "
                                f"— a rising balance implies cash spent on repurchases.")
        )
    if abs(implied_dividends) > 1e-9:
        lines.append(
            ReconstructionLine(
                "implied_dividends", "Implied Dividends Paid", -implied_dividends,
                f"From the retained-earnings bridge: Dividends = PAT − ΔRetained Earnings = "
                f"{current.pat:,.0f} − ({current.retained_earnings:,.0f} − {prior.retained_earnings:,.0f}) "
                f"= {implied_dividends:,.0f}.",
            )
        )
    total = round(sum(l.value for l in lines), 2)
    return {"total": total, "lines": [l.__dict__ for l in lines], "implied_dividends": round(implied_dividends, 2)}


def reconstruct_cash_flow_statement(prior: StatementPeriod, current: StatementPeriod) -> dict[str, Any]:
    """Section G — rebuild the Cash Flow Statement from IS + BS alone."""
    operating = _reconstruct_operating(prior, current)
    investing = _reconstruct_investing(prior, current)
    financing = _reconstruct_financing(prior, current)

    reconstructed_net_change = round(operating["total"] + investing["total"] + financing["total"], 2)
    actual_net_change = round(current.cash - prior.cash, 2)
    residual = round(actual_net_change - reconstructed_net_change, 2)

    return {
        "operating": operating,
        "investing": investing,
        "financing": financing,
        "reconstructed_net_change_in_cash": reconstructed_net_change,
        "actual_net_change_in_cash": actual_net_change,
        "unexplained_residual": residual,
        "reconciles": abs(residual) < max(1.0, 0.01 * max(abs(actual_net_change), 1.0)),
        "honesty_note": (
            "Reconstruction reconciles within tolerance." if abs(residual) < max(1.0, 0.01 * max(abs(actual_net_change), 1.0))
            else f"A residual of {residual:,.0f} remains unexplained by Income Statement + Balance Sheet data alone "
            f"(e.g. FX translation, non-cash equity adjustments, or disposals) — reported explicitly rather than "
            f"forced to zero."
        ),
    }


def verify_reconstruction(prior: StatementPeriod, current: StatementPeriod) -> dict[str, Any]:
    """Compare the reconstruction against the ACTUAL Cash Flow Statement
    fields carried on ``current`` (only usable in testing/validation,
    where the true Cash Flow Statement is known but withheld from the
    reconstruction logic itself)."""
    recon = reconstruct_cash_flow_statement(prior, current)
    return {
        "reconstruction": recon,
        "actual_operating_cf": current.operating_cf,
        "actual_investing_cf": current.investing_cf,
        "actual_financing_cf": current.financing_cf,
        "operating_gap": round((current.operating_cf or 0) - recon["operating"]["total"], 2),
        "investing_gap": round((current.investing_cf or 0) - recon["investing"]["total"], 2),
        "financing_gap": round((current.financing_cf or 0) - recon["financing"]["total"], 2),
    }
