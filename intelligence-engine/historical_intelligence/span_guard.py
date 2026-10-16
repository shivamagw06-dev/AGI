"""Span guard — the rule that stops a real number becoming a false conclusion.

Ask "when was Axis Bank cheapest on price to book" and the honest answer depends
entirely on how far back the P/B series goes. Within a window starting May 2023,
today genuinely is the low. Stated without the window, that becomes "cheapest
ever", which is a fabricated claim built from accurate data.

So every historical answer passes through here first. The guard compares the
period the question asked for against the period the warehouse observed, and
returns the verdict plus the disclosure the answer must carry.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from historical_intelligence import periods
from institutional_warehouse.values import to_date

# Verdicts, in increasing order of what the engine is allowed to claim.
NO_DATA = "no_data"          # nothing observed: no conclusion at all
OUTSIDE = "outside_window"   # asked period sits entirely outside what we hold
PARTIAL = "partial_window"   # asked period only partly observed
COVERED = "covered"          # asked period fully inside the observed window

# A partial window is only worth reasoning over once enough of it is present.
MIN_PARTIAL_OVERLAP = 0.25

# How far behind today a series may sit before the answer says so. Monthly and
# fiscal series legitimately trail; that is freshness, not missing depth.
STALE_BUDGET_DAYS = 120


def _days(start: Optional[str], end: Optional[str]) -> Optional[int]:
    a, b = periods.comparable(start), periods.comparable(end)
    if not a or not b:
        return None
    return max((datetime.fromisoformat(b) - datetime.fromisoformat(a)).days, 0)


def guard(coverage: dict[str, Any], period: dict[str, Any]) -> dict[str, Any]:
    """Decide what may be concluded, given coverage and the asked period."""
    observed_first = coverage.get("earliest")
    observed_last = coverage.get("latest")
    window_label = coverage.get("window_label") or "no observations"
    metric = coverage.get("metric")

    if not coverage.get("observations"):
        return {
            "verdict": NO_DATA,
            "may_conclude": False,
            "observed": None,
            "asked": period.get("label"),
            "window_label": window_label,
            "overlap_pct": 0.0,
            "disclosure": (
                f"AGIB holds no historical {_readable(metric)} observations for "
                f"{coverage.get('symbol')}, so no historical conclusion can be drawn."
            ),
        }

    asked_start, asked_end = period.get("start"), period.get("end")

    # An open or all-time question is answerable over whatever exists, provided the
    # answer names the window — which is why the disclosure is always returned.
    if not asked_start:
        return {
            "verdict": COVERED,
            "may_conclude": True,
            "observed": window_label,
            "asked": period.get("label"),
            "window_label": window_label,
            "overlap_pct": 100.0,
            "full_history_claim_allowed": False,
            "disclosure": (
                f"Observed {_readable(metric)} history runs {window_label}. "
                "Conclusions below are limited to that window."
            ),
        }

    asked_days = _days(asked_start, asked_end) or 0
    observed_from = periods.comparable(observed_first) or str(observed_first)
    observed_to = periods.comparable(observed_last) or str(observed_last)
    overlap_start = max(str(asked_start), observed_from)
    overlap_end = min(str(asked_end), observed_to)
    overlap_days = _days(overlap_start, overlap_end) if overlap_start <= overlap_end else 0
    overlap_days = overlap_days or 0
    ratio = (overlap_days / asked_days) if asked_days else (1.0 if overlap_days else 0.0)
    overlap_pct = round(min(ratio, 1.0) * 100.0, 1)

    # Whether the *depth* asked for exists is decided at the start of the window.
    # A series that stops at last month's close still covers "since 2010"; that
    # trailing gap is a freshness question, reported separately rather than
    # demoting an otherwise complete history to partial.
    depth_covered = observed_from <= str(asked_start)
    stale_days = _days(observed_last, asked_end) or 0

    if depth_covered and overlap_days > 0:
        note = (
            f"Observed {_readable(metric)} history runs {window_label}, which covers "
            f"{period.get('label')}."
        )
        if stale_days > STALE_BUDGET_DAYS:
            note += (
                f" The series has not been updated for {stale_days} days, so the most recent "
                "part of the period asked about is not observed."
            )
        return {
            "verdict": COVERED,
            "may_conclude": True,
            "observed": window_label,
            "asked": period.get("label"),
            "window_label": window_label,
            "overlap_pct": overlap_pct,
            "full_history_claim_allowed": True,
            "stale_days": stale_days,
            "disclosure": note,
        }

    if overlap_days <= 0:
        return {
            "verdict": OUTSIDE,
            "may_conclude": False,
            "observed": window_label,
            "asked": period.get("label"),
            "window_label": window_label,
            "overlap_pct": 0.0,
            "disclosure": (
                f"The question asks about {period.get('label')}, but AGIB's "
                f"{_readable(metric)} history for {coverage.get('symbol')} only covers "
                f"{window_label}. That period is not observed, so no conclusion is drawn."
            ),
        }

    if ratio >= 0.98:
        return {
            "verdict": COVERED,
            "may_conclude": True,
            "observed": window_label,
            "asked": period.get("label"),
            "window_label": window_label,
            "overlap_pct": overlap_pct,
            "full_history_claim_allowed": True,
            "disclosure": (
                f"Observed {_readable(metric)} history runs {window_label}, which covers "
                f"{period.get('label')}."
            ),
        }

    return {
        "verdict": PARTIAL,
        "may_conclude": ratio >= MIN_PARTIAL_OVERLAP,
        "observed": window_label,
        "asked": period.get("label"),
        "window_label": window_label,
        "overlap_pct": overlap_pct,
        "full_history_claim_allowed": False,
        "overlap_from": overlap_start,
        "overlap_to": overlap_end,
        "disclosure": (
            f"The question asks about {period.get('label')}, and AGIB observes "
            f"{_readable(metric)} only from {observed_first} ({overlap_pct}% of the period "
            f"asked). Findings below cover {overlap_start} to {overlap_end}; earlier history "
            "is unavailable, so no claim is made about it."
        ),
    }


def _readable(metric: Optional[str]) -> str:
    labels = {
        "pb": "price-to-book", "pe": "price-to-earnings", "ev_ebitda": "EV/EBITDA",
        "ev_sales": "EV/Sales", "price_sales": "price-to-sales",
        "dividend_yield": "dividend yield", "market_cap": "market capitalisation",
        "roe": "return on equity", "roce": "return on capital",
        "net_margin": "net margin", "ebitda_margin": "EBITDA margin",
        "debt_equity": "debt-to-equity", "free_cash_flow": "free cash flow",
        "price": "share price", "revenue": "revenue", "pat": "profit",
        "eps": "earnings per share", "target_price": "consensus target",
        "promoter_holding": "promoter holding",
    }
    return labels.get(str(metric), str(metric or "").replace("_", " "))


def extreme_claim_allowed(guard_result: dict[str, Any]) -> bool:
    """A 'cheapest ever' style claim needs the full history, not a slice of it."""
    return bool(guard_result.get("full_history_claim_allowed")) and \
        guard_result.get("verdict") == COVERED


def qualify_extreme(guard_result: dict[str, Any], coverage: dict[str, Any]) -> str:
    """The phrase an extreme must be wrapped in, given what is observed."""
    if extreme_claim_allowed(guard_result):
        return "across the observed history"
    years = coverage.get("years")
    span = coverage.get("window_label")
    if years and years >= 10:
        return f"within the {years:.0f} years observed ({span})"
    return f"within the observed window only ({span})"
