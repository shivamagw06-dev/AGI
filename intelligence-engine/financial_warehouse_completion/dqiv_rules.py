"""FWCP DQIV — reject impossible statement / share-count facts before warehouse write."""

from __future__ import annotations

from typing import Any, Optional

from institutional_warehouse.values import to_number


def _n(value: Any) -> Optional[float]:
    return to_number(value)


def validate_share_count_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return {ok, status, notes, confidence}."""
    notes: list[str] = []
    shares = _n(row.get("shares_outstanding"))
    basic = _n(row.get("basic_shares"))
    diluted = _n(row.get("diluted_shares"))
    weighted = _n(row.get("weighted_average_shares"))
    candidates = [v for v in (shares, basic, diluted, weighted) if v is not None]
    if not candidates:
        return {"ok": False, "status": "fail", "notes": ["missing_share_count"], "confidence": 0.0}
    if any(v <= 0 for v in candidates):
        return {"ok": False, "status": "fail", "notes": ["non_positive_share_count"], "confidence": 0.0}
    if diluted is not None and basic is not None and diluted + 1e-6 < basic:
        notes.append("diluted_below_basic")
    conf = 0.9 if shares or diluted or weighted else 0.6
    if notes:
        conf = min(conf, 0.55)
    return {
        "ok": True,
        "status": "warn" if notes else "ok",
        "notes": notes,
        "confidence": conf,
        "canonical_shares": shares or diluted or weighted or basic,
    }


def validate_statement_row(row: dict[str, Any], *, quarterly: bool = False) -> dict[str, Any]:
    """Lightweight institutional statement checks (material tolerance)."""
    notes: list[str] = []
    assets = _n(row.get("total_assets"))
    liabilities = _n(row.get("total_liabilities"))
    equity = _n(row.get("total_equity") or row.get("equity") or row.get("shareholders_equity"))
    shares = _n(row.get("shares_outstanding"))
    revenue = _n(row.get("revenue") or row.get("total_revenue"))

    if shares is not None and shares <= 0:
        return {"ok": False, "status": "fail", "notes": ["non_positive_share_count"], "confidence": 0.0}

    if assets is not None and liabilities is not None and equity is not None:
        lhs = assets
        rhs = liabilities + equity
        if rhs != 0:
            gap = abs(lhs - rhs) / abs(rhs)
            if gap > 0.05:
                notes.append(f"balance_sheet_imbalance_{gap:.1%}")
                if gap > 0.25:
                    return {
                        "ok": False,
                        "status": "fail",
                        "notes": notes,
                        "confidence": 0.1,
                    }

    period = row.get("fiscal_year") if not quarterly else row.get("fiscal_period")
    if not period:
        notes.append("missing_reporting_period")

    currency = str(row.get("currency") or "INR").upper()
    if currency not in {"INR", "USD", "EUR", "GBP", "JPY", ""}:
        notes.append(f"unexpected_currency_{currency}")

    if revenue is not None and revenue < 0:
        notes.append("negative_revenue")

    status = "fail" if any(n.startswith("missing_") for n in notes) else ("warn" if notes else "ok")
    ok = status != "fail"
    conf = 0.85 if status == "ok" else (0.5 if status == "warn" else 0.2)
    return {"ok": ok, "status": status, "notes": notes, "confidence": conf}


def reject_vendor_multiples(row: dict[str, Any]) -> list[str]:
    """Flag rows that try to smuggle historical PE/PB/EV into statement packs."""
    from financial_warehouse_completion.models import FORBIDDEN_VENDOR_MULTIPLES

    hits = []
    for key in FORBIDDEN_VENDOR_MULTIPLES:
        if row.get(key) is not None and key not in {"shares_outstanding"}:
            # Allow presence only if explicitly marked reconstructed.
            src = str(row.get("source") or "").lower()
            if "reconstruction" not in src and "formula" not in src:
                hits.append(key)
    return hits
