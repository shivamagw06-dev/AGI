"""Bridge Yahoo/CID/DVC field paths to company_analysis readers.

Architecture v1.0.1 LOCKED — additive soft-wire only.
Never expose provider names. Unwrap validated field objects to bare values.
"""

from __future__ import annotations

from typing import Any


def unwrap_value(v: Any) -> Any:
    """DVC validated fields are often {value, provider, ...} — keep the number only."""
    if isinstance(v, dict):
        if "value" in v and v.get("value") not in (None, ""):
            return v.get("value")
        for nested in ("last", "metric", "amount", "score"):
            if nested in v and v.get(nested) not in (None, ""):
                return v.get(nested)
    return v


def unwrap_validated(fields: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (fields or {}).items():
        out[k] = unwrap_value(v)
    return out


def normalise_financials(cid: dict[str, Any] | None) -> dict[str, Any]:
    """Merge institutional financials with soft-enriched financial_metrics."""
    cid = cid or {}
    institutional = dict(cid.get("financials") or cid.get("financial_intelligence") or {})
    soft = dict(cid.get("financial_metrics") or {})
    # Soft fills gaps only — institutional wins on collision
    merged = {**soft, **institutional}
    # Alias Yahoo-shaped keys to analysis readers
    if merged.get("net_margin") is None and merged.get("profit_margin") is not None:
        merged["net_margin"] = merged["profit_margin"]
    if merged.get("npm") is None and merged.get("net_margin") is not None:
        merged["npm"] = merged["net_margin"]
    if merged.get("fcf") is None and merged.get("free_cash_flow") is not None:
        merged["fcf"] = merged["free_cash_flow"]
    if merged.get("operating_cash_flow") is None and merged.get("operatingCashFlow") is not None:
        merged["operating_cash_flow"] = merged["operatingCashFlow"]
    return merged


def normalise_valuation(cid: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten nested valuation.current into analysis-friendly keys."""
    cid = cid or {}
    val = dict(cid.get("valuation") or {})
    curr = dict(val.get("current") or {})
    md_mult = dict(((cid.get("market_data") or {}).get("valuation_multiples") or {}))
    flat = {
        "pe": val.get("pe") or curr.get("trailing_pe") or md_mult.get("trailing_pe"),
        "trailing_pe": curr.get("trailing_pe") or md_mult.get("trailing_pe") or val.get("pe"),
        "forward_pe": curr.get("forward_pe") or md_mult.get("forward_pe") or val.get("forward_pe"),
        "pb": val.get("pb") or curr.get("price_to_book") or md_mult.get("price_to_book"),
        "price_to_book": curr.get("price_to_book") or md_mult.get("price_to_book") or val.get("pb"),
        "ps": val.get("ps") or curr.get("price_to_sales") or md_mult.get("price_to_sales"),
        "peg": val.get("peg") or curr.get("peg") or md_mult.get("peg"),
        "ev_ebitda": val.get("ev_ebitda") or curr.get("ev_ebitda") or md_mult.get("ev_ebitda"),
        "enterprise_value": curr.get("enterprise_value") or md_mult.get("enterprise_value") or val.get("enterprise_value"),
        "market_cap": curr.get("market_cap") or (cid.get("market_data") or {}).get("market_cap") or val.get("market_cap"),
        "dividend_yield": (cid.get("market_data") or {}).get("dividend_yield") or val.get("dividend_yield"),
        "target_mean_price": curr.get("target_mean_price") or val.get("target_mean_price"),
        "historical_pe": val.get("historical_pe") or val.get("pe_median") or val.get("avg_pe"),
        "peer_pe": val.get("peer_pe") or val.get("sector_pe"),
        "expected_growth": val.get("expected_growth"),
        "intrinsic_value": val.get("intrinsic_value"),
        "margin_of_safety": val.get("margin_of_safety"),
        "pe_range": val.get("pe_range") or val.get("historical_range"),
        "historical_range": val.get("historical_range") or val.get("pe_range"),
        "confidence": val.get("confidence"),
    }
    # Preserve remaining valuation keys without nested current
    for k, v in val.items():
        if k in {"current", "historical", "timeline"}:
            continue
        if flat.get(k) is None and v not in (None, "", []):
            flat[k] = v
    return flat


def normalise_business_model(cid: dict[str, Any] | None) -> str | None:
    cid = cid or {}
    return (
        cid.get("business_model")
        or ((cid.get("business_profile") or {}).get("business_model"))
        or ((cid.get("identity") or {}).get("business_model"))
        or None
    )


def normalise_kpi_trends(hist: dict[str, Any] | None) -> dict[str, Any]:
    hist = hist or {}
    trends = dict(hist.get("trends") or {}) if isinstance(hist.get("trends"), dict) else {}
    if trends:
        return trends
    kpi = hist.get("kpi_trends") if isinstance(hist.get("kpi_trends"), dict) else {}
    if not kpi and isinstance(hist, dict):
        # Sometimes KPI trends live at cid.historical_kpi_trends
        pass
    for k, v in kpi.items():
        if isinstance(v, list) and len(v) >= 2:
            try:
                a, b = float(v[0]), float(v[-1])
                trends[k] = "improving" if b > a else "deteriorating" if b < a else "stable"
            except (TypeError, ValueError):
                trends[k] = "stable"
        elif isinstance(v, str):
            trends[k] = v
    return trends


def market_snapshot(cid: dict[str, Any] | None) -> dict[str, Any]:
    """Canonical market quote / range signals from CID (provider-agnostic)."""
    cid = cid or {}
    md = dict(cid.get("market_data") or {})
    quote_bits = {
        "current_price": md.get("current_price"),
        "volume": md.get("volume"),
        "market_cap": md.get("market_cap") or ((cid.get("identity") or {}).get("market_cap")),
        "fifty_two_week_high": md.get("fifty_two_week_high"),
        "fifty_two_week_low": md.get("fifty_two_week_low"),
        "dividend_yield": md.get("dividend_yield"),
        "beta": md.get("beta"),
        "enterprise_value": md.get("enterprise_value"),
        "exchange": md.get("exchange") or (cid.get("identity") or {}).get("exchange"),
        "currency": md.get("currency") or "INR",
        "open": md.get("open") or md.get("day_open"),
        "high": md.get("high") or md.get("day_high"),
        "low": md.get("low") or md.get("day_low"),
        "change_pct": md.get("change_pct") or md.get("daily_change_pct"),
    }
    # Range position for interpretive momentum
    price = quote_bits.get("current_price")
    hi = quote_bits.get("fifty_two_week_high")
    lo = quote_bits.get("fifty_two_week_low")
    range_pos = None
    try:
        if price is not None and hi is not None and lo is not None and float(hi) > float(lo):
            range_pos = round((float(price) - float(lo)) / (float(hi) - float(lo)), 3)
    except (TypeError, ValueError, ZeroDivisionError):
        range_pos = None
    quote_bits["range_position_0_1"] = range_pos
    return {k: v for k, v in quote_bits.items() if v is not None}


def ownership_snapshot(cid: dict[str, Any] | None) -> dict[str, Any]:
    cid = cid or {}
    own = dict(((cid.get("peer_comparison") or {}).get("ownership") or {}))
    mgmt = dict(cid.get("management") or {})
    return {
        "institutions_percent": own.get("institutions_percent"),
        "insiders_percent": own.get("insiders_percent"),
        "funds_percent": own.get("funds_percent"),
        "ceo": mgmt.get("ceo"),
        "cfo": mgmt.get("cfo"),
        "board": mgmt.get("board") if isinstance(mgmt.get("board"), list) else [],
    }
