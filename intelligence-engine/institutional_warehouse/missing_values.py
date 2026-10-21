"""Missing Value Intelligence — a zero is not always a number.

Production narrated "return on equity rose from 0 in FY19" because a missing
statement line was stored as 0 and then read as an observation. The fix is not a
global rule: some zeros are real. No dividend declared is genuinely zero. A stock
that did not trade genuinely has zero volume. But a bank with zero return on
equity, zero revenue or zero equity is a gap in the data wearing a number.

So the policy is per field, and every classified value carries why it was
classified that way.
"""

from __future__ import annotations

from typing import Any, Optional

from institutional_warehouse.values import is_blank, to_number

# Observation classes.
OBSERVED = "observed"
MISSING = "missing"
NOT_APPLICABLE = "not_applicable"
SUPPRESSED = "suppressed"

# Fields where zero is a real reading and must be preserved.
ZERO_IS_REAL = frozenset({
    "dividend", "split", "bonus", "rights", "buyback",
    "volume", "delivery_pct", "trades",
    "buy", "outperform", "hold", "sell", "no_opinion", "analyst_count",
    "promoter_holding", "insider_holding", "fii", "dii", "mutual_funds",
    "capex", "debt", "cash", "target_dispersion",
})

# Fields where zero cannot describe a going concern and means the line is absent.
ZERO_IS_MISSING = frozenset({
    "revenue", "equity", "assets", "shares_outstanding", "book_value",
    "roe", "roce", "roa", "gross_margin", "ebitda_margin", "operating_margin",
    "net_margin", "asset_turnover", "fcf_margin", "current_ratio", "quick_ratio",
    "pe", "forward_pe", "pb", "ev_ebitda", "ev_sales", "price_sales", "peg",
    "cmp", "close", "open", "high", "low", "adjusted_close", "vwap",
    "market_cap", "enterprise_value", "target_price", "high_target", "low_target",
    "confidence",
})

# Fields that may legitimately be negative or zero — a loss-making year is real.
SIGNED_FIELDS = frozenset({
    "pat", "pbt", "ebit", "ebitda", "eps", "free_cash_flow", "cfo", "cfi", "cff",
    "working_capital", "gross_profit", "upside", "change_pct",
})


def classify(field: str, value: Any, *, source: Optional[str] = None) -> dict[str, Any]:
    """Decide whether a value is an observation, and say why."""
    key = str(field or "").strip().lower()

    if is_blank(value):
        return {"status": MISSING, "value": None,
                "reason": "no value supplied by the source", "source": source}

    number = to_number(value)
    if number is None:
        # Non-numeric fields are observations whenever they carry text.
        return {"status": OBSERVED, "value": value, "reason": "non-numeric value present",
                "source": source}

    if number == 0:
        if key in ZERO_IS_REAL:
            return {"status": OBSERVED, "value": 0.0,
                    "reason": "zero is a real reading for this field", "source": source}
        if key in ZERO_IS_MISSING:
            return {
                "status": MISSING,
                "value": None,
                "reason": (
                    f"zero {key} cannot describe a going concern, so the line is treated as "
                    "absent rather than observed"
                ),
                "source": source,
            }
        if key in SIGNED_FIELDS:
            return {"status": OBSERVED, "value": 0.0,
                    "reason": "break-even is a real outcome for this field", "source": source}
        # Unknown field: keep the value but flag it for review rather than guessing.
        return {"status": OBSERVED, "value": 0.0,
                "reason": "zero retained; no missing-value policy for this field",
                "source": source, "unpoliced": True}

    return {"status": OBSERVED, "value": number if _numeric_field(key) else value,
            "reason": "value supplied by the source", "source": source}


def _numeric_field(key: str) -> bool:
    return key in ZERO_IS_REAL or key in ZERO_IS_MISSING or key in SIGNED_FIELDS


def apply(row: dict[str, Any], *, source: Optional[str] = None) -> dict[str, Any]:
    """Classify a whole row. Missing values become None, never zero."""
    cleaned: dict[str, Any] = {}
    missing: list[str] = []
    coerced: list[dict[str, Any]] = []

    for field, value in row.items():
        if field.startswith("sys_") or field in ("row_id", "_meta"):
            cleaned[field] = value
            continue
        verdict = classify(field, value, source=source)
        cleaned[field] = verdict["value"]
        if verdict["status"] == MISSING:
            missing.append(field)
            if not is_blank(value):
                # A zero that has been reclassified: worth recording, it is a source defect.
                coerced.append({"field": field, "was": value, "reason": verdict["reason"]})

    return {
        "row": cleaned,
        "missing_fields": missing,
        "reclassified_zeros": coerced,
        "observed_fields": [f for f in cleaned
                            if not f.startswith("sys_") and cleaned[f] is not None],
    }


def is_observation(field: str, value: Any) -> bool:
    """The question every reasoning engine should ask before narrating a number."""
    return classify(field, value)["status"] == OBSERVED
