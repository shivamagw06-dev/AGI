"""Independent checks on warehouse ratios before a Hedge Fund screen ranks them.

The Quality desk was ranking Algoquant on a `FY26` formula row (80% net
margin, D/E printed as 25x) while a `FY2026` Capital IQ row for the same year
reconciled to PAT/revenue. String-max period selection preferred `FY26` over
`FY2026`. This module picks the fiscal year correctly and flags ratios that
cannot be the company's reported figures.
"""

from __future__ import annotations

import re
from typing import Any, Optional

_FY = re.compile(r"FY\s*(20)?(\d{2})", re.I)
_Q = re.compile(r"Q([1-4])", re.I)

# Net profit / revenue above this is treated as a mapping error, not a business.
NET_MARGIN_HARD_MAX = 65.0
NET_MARGIN_HARD_MIN = -80.0
# Debt/equity as a multiple. 25.5 is 0.255 stored as percent.
DEBT_EQUITY_HARD_MAX = 8.0
ROE_HARD_MAX = 120.0
# Vendor TTM vs annual ROE often differs; flag, do not replace, above this.
ROE_VENDOR_GAP_PP = 8.0
# PAT/revenue vs the stored net-margin print.
INDEPENDENT_MARGIN_TOLERANCE_PP = 2.0


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def fiscal_period_key(period: Any) -> tuple:
    """Sort key: later fiscal year wins; `FY2026` beats the same year labelled `FY26`."""
    text = str(period or "").strip().upper()
    match = _FY.search(text)
    if not match:
        return (0, 0, 0, text)
    year = 2000 + int(match.group(2))
    four_digit = 1 if match.group(1) else 0
    quarter = 0
    qmatch = _Q.search(text)
    if qmatch:
        quarter = int(qmatch.group(1))
    return (year, four_digit, quarter, text)


def pick_latest_annual_ratio(rows: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Latest fiscal year that survives the ratio audit; otherwise the latest row.

    `FY26` sorts after `FY2026` as a string (`'6' > '0'`), which is how a
    broken formula row outranked the Capital IQ year for Algoquant. The sort
    key fixes that, and a failing year is skipped when a passing one exists.
    """
    annual = [
        row for row in rows
        if str(row.get("basis") or "").lower() in ("", "annual")
        and str(row.get("symbol") or "").strip()
    ]
    if not annual:
        return None
    ranked = sorted(annual, key=lambda row: fiscal_period_key(row.get("period")), reverse=True)
    for row in ranked:
        audit = audit_quality_metrics(
            roe=_num(row.get("roe")),
            net_margin=_num(row.get("net_margin")),
            debt_equity=_num(row.get("debt_equity")),
            gross_margin=_num(row.get("gross_margin")),
            ebitda_margin=_num(row.get("ebitda_margin")),
        )
        if audit["status"] == "pass":
            return row
    return ranked[0]


def audit_quality_metrics(
    *,
    roe: Optional[float],
    net_margin: Optional[float],
    debt_equity: Optional[float],
    vendor_roe: Optional[float] = None,
    gross_margin: Optional[float] = None,
    ebitda_margin: Optional[float] = None,
    computed_net_margin: Optional[float] = None,
) -> dict[str, Any]:
    """Compare printed quality fields against hard bounds and an independent print.

    Order: stored ratio → PAT/revenue (when supplied) → vendor TTM → tolerance.
    Returns status `pass` or `data_quality_fail`. Callers must not mark a fail
    as screen-validated.
    """
    reasons: list[str] = []
    warnings: list[str] = []
    if net_margin is not None and not (NET_MARGIN_HARD_MIN <= net_margin <= NET_MARGIN_HARD_MAX):
        reasons.append(
            f"net_margin {net_margin}% is outside {NET_MARGIN_HARD_MIN} to {NET_MARGIN_HARD_MAX} "
            "and is not a plausible PAT/revenue figure"
        )
    if computed_net_margin is not None and net_margin is not None:
        gap = round(net_margin - computed_net_margin, 2)
        if abs(gap) > INDEPENDENT_MARGIN_TOLERANCE_PP:
            reasons.append(
                f"stored net_margin {net_margin}% disagrees with PAT/revenue "
                f"{computed_net_margin}% by {gap}pp"
            )
    if (
        net_margin is not None
        and ebitda_margin is not None
        and ebitda_margin > 0
        and net_margin > ebitda_margin + 5
    ):
        reasons.append(
            f"net_margin {net_margin}% exceeds ebitda_margin {ebitda_margin}%"
        )
    if net_margin is not None and gross_margin is not None:
        if 0 < gross_margin < net_margin:
            reasons.append(
                f"net_margin {net_margin}% exceeds gross_margin {gross_margin}%"
            )
        if gross_margin < 0 and net_margin > 20:
            reasons.append(
                f"net_margin {net_margin}% with gross_margin {gross_margin}% "
                "is a field-mapping error, not a business"
            )
    if debt_equity is not None and not (0 <= debt_equity <= DEBT_EQUITY_HARD_MAX):
        reasons.append(
            f"debt_equity {debt_equity} is outside 0–{DEBT_EQUITY_HARD_MAX}x; "
            "a figure near 25 usually means percent was stored as a multiple"
        )
    if roe is not None and abs(roe) > ROE_HARD_MAX:
        reasons.append(f"roe {roe}% is outside ±{ROE_HARD_MAX}")
    vendor_gap = None
    if roe is not None and vendor_roe is not None:
        vendor_gap = round(roe - vendor_roe, 2)
        if abs(vendor_gap) >= ROE_VENDOR_GAP_PP:
            warnings.append(
                f"annual ROE {roe}% differs from vendor TTM {vendor_roe}% by {vendor_gap}pp"
            )
    return {
        "status": "data_quality_fail" if reasons else "pass",
        "reasons": reasons,
        "warnings": warnings,
        "vendor_roe_gap_pp": vendor_gap,
        "computed_net_margin": computed_net_margin,
    }
