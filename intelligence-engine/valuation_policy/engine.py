"""Valuation Policy & Applicability Engine — core decision layer.

Extends ``valuation_terminal.sector_lens`` with instrument type, profitability,
financial coverage and DQIV so no consumer independently decides which
multiple to show.
"""

from __future__ import annotations

from typing import Any, Optional

from valuation_policy.instruments import resolve_instrument
from valuation_policy.models import (
    COVERAGE_LEVELS,
    ENGINE_CODE,
    EXTREME_EV_EBITDA,
    EXTREME_PB,
    EXTREME_PE,
    METRIC_TO_MODEL,
    VERSION,
)

# DNA families that never flip to EV/Sales on loss-making EPS — balance-sheet
# models stay primary.
_BALANCE_SHEET_DNA = frozenset({"banks", "nbfc", "insurance", "real_estate", "reit", "invit"})
_FINANCIAL_DNA = frozenset({"banks", "nbfc", "insurance", "asset_management"})

# DNA where profitable internet/retail should prefer PE.
_PROFIT_FLIP_DNA = frozenset({"internet_platforms", "retail", "software", "qsr"})


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _model(metric: str) -> str:
    return METRIC_TO_MODEL.get(metric, str(metric or "").upper())


def _resolve_dna(master: dict[str, Any], industry_hint: Optional[str] = None) -> dict[str, Any]:
    """Prefer CapIQ identity DNA; fall back to master industry / sector_lens keys."""
    sector = master.get("sector")
    industry = industry_hint or master.get("industry") or master.get("primary_industry")
    dna = master.get("industry_dna")
    business_type = master.get("business_type")
    source = "company_master"

    if not dna:
        try:
            from company_identity.taxonomy import classify

            business_type, dna = classify(industry, sector)
            source = "taxonomy.classify"
        except Exception:
            dna = None

    if not dna and industry:
        # UVE historically stuffed DNA keys into master.industry.
        try:
            from valuation_terminal.sector_lens import _LENS

            key = str(industry).strip().lower().replace(" ", "_").replace("-", "_")
            if key in _LENS:
                dna = key
                source = "master.industry_as_dna"
        except Exception:
            pass

    return {
        "industry_dna": dna,
        "business_type": business_type,
        "sector": sector,
        "industry": industry,
        "source": source,
    }


def _financial_health(record: dict[str, Any]) -> dict[str, Any]:
    annual = record.get("latest_annual") or {}
    price = record.get("latest_price") or {}
    provider = ((record.get("provider_ratios") or {}).get("ratios") or {})

    eps = _num(annual.get("eps"))
    pat = _num(annual.get("pat") or annual.get("net_income") or annual.get("profit_after_tax"))
    ebitda = _num(annual.get("ebitda"))
    revenue = _num(annual.get("revenue") or annual.get("sales"))
    equity = _num(annual.get("equity") or annual.get("shareholders_equity") or annual.get("book_value"))
    book_ps = _num(annual.get("book_value"))
    if book_ps is None and equity is not None:
        shares = _num(price.get("shares_outstanding") or annual.get("shares_outstanding"))
        if shares and shares > 0:
            # equity is typically INR million; leave as availability flag only.
            book_ps = equity

    cash = _num(annual.get("cash"))
    debt = _num(annual.get("debt") or annual.get("total_debt"))
    shares = _num(price.get("shares_outstanding") or annual.get("shares_outstanding"))
    cmp = _num(price.get("close") or price.get("ltp") or price.get("price"))

    def _provider_num(key: str) -> Optional[float]:
        cell = provider.get(key)
        if not isinstance(cell, dict):
            return _num(cell)
        return _num(
            cell.get("company_value")
            if cell.get("company_value") is not None
            else cell.get("value") or cell.get("ratio_value")
        )

    pe = _provider_num("pe")
    pb = _provider_num("pb")
    ev_ebitda = _provider_num("ev_ebitda")
    if eps is None and pe is not None and pe < 0:
        eps = -1.0

    negative_earnings = (eps is not None and eps < 0) or (pat is not None and pat < 0)
    positive_earnings = (eps is not None and eps > 0) or (pat is not None and pat > 0)

    missing: list[str] = []
    if eps is None and pat is None:
        missing.append("earnings")
    if revenue is None:
        missing.append("revenue")
    if ebitda is None:
        missing.append("ebitda")
    if equity is None and book_ps is None:
        missing.append("shareholders_equity")
    if shares is None:
        missing.append("shares_outstanding")
    if cmp is None:
        missing.append("market_price")
    if debt is None:
        missing.append("total_debt")
    if cash is None:
        missing.append("cash")

    return {
        "eps": eps,
        "pat": pat,
        "ebitda": ebitda,
        "revenue": revenue,
        "equity": equity,
        "book_value_per_share": book_ps,
        "shares_outstanding": shares,
        "cmp": cmp,
        "debt": debt,
        "cash": cash,
        "pe": pe,
        "pb": pb,
        "ev_ebitda": ev_ebitda,
        "positive_earnings": positive_earnings,
        "negative_earnings": negative_earnings,
        "positive_ebitda": ebitda is not None and ebitda > 0,
        "negative_ebitda": ebitda is not None and ebitda < 0,
        "has_book_value": equity is not None or book_ps is not None,
        "has_revenue": revenue is not None and revenue > 0,
        "has_enterprise_inputs": shares is not None and cmp is not None,
        "missing_fields": missing,
    }


def _baseline_lens(industry_dna: Optional[str], sector: Optional[str]) -> dict[str, Any]:
    from valuation_terminal.sector_lens import lens_for

    return lens_for(industry_dna, sector) or {}


def _coverage_block(health: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    missing = list(health.get("missing_fields") or [])
    statement = "FULL" if not {"earnings", "revenue", "shareholders_equity"} & set(missing) else (
        "NONE" if len(missing) >= 5 else "PARTIAL"
    )
    market = "FULL" if health.get("cmp") is not None else "NONE"
    hist = record.get("coverage") if isinstance(record.get("coverage"), dict) else {}
    historical = "PARTIAL"
    if hist:
        # warehouse company_view coverage is a dict of tab → counts when present
        vals = [v for v in hist.values() if isinstance(v, (int, float))]
        if vals and max(vals) >= 5:
            historical = "FULL"
        elif vals and max(vals) > 0:
            historical = "PARTIAL"
        else:
            historical = "THIN"
    elif record.get("ratios") or record.get("valuation"):
        historical = "PARTIAL"
    else:
        historical = "THIN"

    ranks = {level: i for i, level in enumerate(COVERAGE_LEVELS)}
    overall_rank = min(ranks.get(statement, 3), ranks.get(market, 3), ranks.get(historical, 3))
    overall = COVERAGE_LEVELS[overall_rank]
    return {
        "financial_coverage": statement,
        "statement_coverage": statement,
        "market_coverage": market,
        "historical_coverage": historical,
        "coverage": overall,
        "missing_fields": missing,
    }


def _metric_entry(
    metric: str,
    *,
    state: str,
    reason: str,
    confidence: str = "HIGH",
    source: str = ENGINE_CODE,
) -> dict[str, Any]:
    return {
        "metric": metric,
        "model": _model(metric),
        "status": state,
        "reason": reason,
        "confidence": confidence,
        "source": source,
    }


def evaluate(
    symbol: str,
    *,
    record: Optional[dict[str, Any]] = None,
    industry_dna: Optional[str] = None,
) -> dict[str, Any]:
    """Produce the institutional valuation policy for one company.

    Does not compute multiples — only decides which models apply.
    """
    ticker = str(symbol or "").strip().upper()
    if record is None:
        try:
            from institutional_warehouse.production import read_company

            record = read_company(ticker)
        except Exception as exc:
            return {
                "ok": False,
                "symbol": ticker,
                "error": f"warehouse_unavailable:{exc}",
                "engine": ENGINE_CODE,
                "version": VERSION,
            }

    if not record or not record.get("ok", True):
        return {
            "ok": False,
            "symbol": ticker,
            "error": "not_in_warehouse",
            "status": "INSUFFICIENT_DATA",
            "engine": ENGINE_CODE,
            "version": VERSION,
        }

    master = dict(record.get("master") or {})
    identity = _resolve_dna(master, industry_dna)
    dna = identity["industry_dna"]
    sector = identity["sector"]
    company_name = master.get("company_name") or ticker

    instrument = resolve_instrument(
        symbol=ticker,
        company_name=company_name,
        sector=sector,
        industry=identity["industry"],
        industry_dna=dna,
        master=master,
    )
    instrument_type = instrument["instrument_type"]

    # Instrument DNA override so sector_lens baseline matches product class.
    if instrument_type in {"ETF", "COMMODITY_ETF", "MUTUAL_FUND", "INDEX"}:
        dna = "etf"
    elif instrument_type == "REIT":
        dna = "reit"
    elif instrument_type == "INVIT":
        dna = "invit"

    health = _financial_health(record)
    coverage = _coverage_block(health, record)
    lens = _baseline_lens(dna, sector)

    primary = lens.get("primary_metric") or "pe"
    supporting = list(lens.get("supporting_metrics") or [])
    hidden = list(lens.get("suppressed_metrics") or [])
    rationale = lens.get("rationale") or ""
    status = "VALID"
    confidence = "HIGH"
    reason_codes: list[str] = ["SECTOR_BASELINE"]
    reason = rationale or "Industry baseline valuation policy from sector_lens."

    # --- Instrument overrides ------------------------------------------------
    if instrument_type in {"ETF", "COMMODITY_ETF", "MUTUAL_FUND", "INDEX"}:
        primary = "price"
        supporting = ["market_cap"]
        hidden = ["pe", "pb", "ev_ebitda", "ev_sales", "ps", "roe", "roa", "roce", "eps"]
        status = "ETF" if instrument_type != "INDEX" else "NOT_APPLICABLE"
        reason = (
            f"{instrument_type.replace('_', ' ').title()} instruments are valued on NAV / "
            "tracking characteristics, not company earnings multiples."
        )
        reason_codes = ["INSTRUMENT_ETF" if status == "ETF" else "INSTRUMENT_INDEX"]
        confidence = instrument.get("confidence") or "HIGH"
    elif instrument_type == "REIT":
        primary = "pb"  # Price/NAV until dedicated NAV lands
        supporting = ["dividend_yield", "roe"]
        hidden = ["pe", "ev_ebitda", "ev_sales"]
        status = "REIT"
        reason = "REITs are primarily valued on Price/NAV and distribution yield, not P/E."
        reason_codes = ["INSTRUMENT_REIT"]
    elif instrument_type == "INVIT":
        primary = "pb"
        supporting = ["dividend_yield"]
        hidden = ["pe", "ev_ebitda", "ev_sales"]
        status = "INVIT"
        reason = "InvITs are primarily valued on Price/NAV and yield."
        reason_codes = ["INSTRUMENT_INVIT"]
    elif dna == "banks":
        status = "BANKING_MODEL"
        primary = "pb"
        reason = (
            "Deposit-taking financial institutions are primarily valued using "
            "Price-to-Book because enterprise value is not meaningful."
        )
        reason_codes = ["BANKING_MODEL"]
    elif dna == "nbfc":
        status = "NBFC_MODEL"
        primary = "pb"
        reason = "NBFCs are primarily valued on Price-to-Book with ROE and credit-cost context."
        reason_codes = ["NBFC_MODEL"]
    elif dna == "insurance":
        status = "INSURANCE_MODEL"
        primary = "pb"  # Price-to-EV fallback until embedded value feed exists
        reason = (
            "Insurers are primarily valued on Price to Embedded Value; AGIB falls "
            "back to Price-to-Book until embedded value is available."
        )
        reason_codes = ["INSURANCE_MODEL", "EMBEDDED_VALUE_FALLBACK"]
        confidence = "MEDIUM"

    # --- Profitability overrides (non-financial equities) --------------------
    if (
        instrument_type == "EQUITY"
        and dna not in _BALANCE_SHEET_DNA
        and dna != "etf"
        and health["negative_earnings"]
    ):
        if "pe" not in hidden:
            hidden.append("pe")
        if primary == "pe":
            primary = "ev_sales" if health["has_revenue"] else "ps"
        if primary in supporting:
            supporting = [m for m in supporting if m != primary]
        for extra in ("revenue_growth", "gross_margin", "cash_burn", "ev_sales", "ps"):
            if extra not in supporting and extra != primary:
                # only keep metrics the terminal understands in supporting list for UI
                if extra in {"ev_sales", "ps"} and extra not in supporting:
                    supporting.append(extra)
        status = "LOSS_MAKING"
        reason = (
            "Negative trailing earnings — Price-to-Earnings is not meaningful. "
            f"Primary valuation model set to {_model(primary)}."
        )
        reason_codes = list(dict.fromkeys([*reason_codes, "LOSS_MAKING", "PE_SUPPRESSED"]))
        confidence = "HIGH"
    elif (
        instrument_type == "EQUITY"
        and dna in _PROFIT_FLIP_DNA
        and health["positive_earnings"]
        and primary in {"ev_sales", "ps"}
        and status == "VALID"
    ):
        # Profitable platforms / retail: prefer PE.
        if "pe" in hidden:
            hidden = [m for m in hidden if m != "pe"]
        if primary not in supporting:
            supporting = [primary, *supporting]
        primary = "pe"
        reason = (
            "Business is currently profitable; Price-to-Earnings is the primary "
            "valuation model with growth multiples as support."
        )
        reason_codes = list(dict.fromkeys([*reason_codes, "PROFITABLE_FLIP_TO_PE"]))

    # Telecom / airlines — hide distorted PE when extreme or negative.
    if dna in {"telecom", "airlines"} and instrument_type == "EQUITY":
        pe_val = health.get("pe")
        if health["negative_earnings"] or (pe_val is not None and abs(pe_val) > EXTREME_PE):
            if "pe" not in hidden:
                hidden.append("pe")
            reason_codes = list(dict.fromkeys([*reason_codes, "PE_DISTORTED"]))
            if status == "VALID":
                status = "EXTREME_VALUATION" if pe_val and abs(pe_val) > EXTREME_PE else status

    # --- Extreme multiples: classify, never reject ----------------------------
    extreme_notes: list[str] = []
    pe_val = health.get("pe")
    pb_val = health.get("pb")
    ev_val = health.get("ev_ebitda")
    if pe_val is not None and pe_val > EXTREME_PE and "pe" not in hidden:
        extreme_notes.append(f"PE={pe_val:.1f} above institutional extreme threshold ({EXTREME_PE:g}).")
    if pb_val is not None and pb_val > EXTREME_PB and "pb" not in hidden:
        extreme_notes.append(f"P/B={pb_val:.1f} above institutional extreme threshold ({EXTREME_PB:g}).")
    if ev_val is not None and ev_val > EXTREME_EV_EBITDA and "ev_ebitda" not in hidden:
        extreme_notes.append(
            f"EV/EBITDA={ev_val:.1f} above institutional extreme threshold ({EXTREME_EV_EBITDA:g})."
        )
    if extreme_notes and status in {"VALID", "BANKING_MODEL", "NBFC_MODEL", "INSURANCE_MODEL"}:
        status = "EXTREME_VALUATION"
        reason_codes = list(dict.fromkeys([*reason_codes, "EXTREME_VALUATION"]))
        reason = f"{reason} {' '.join(extreme_notes)} Classified as Extreme Valuation (warning, not error)."

    # --- Missing data / unavailable models -----------------------------------
    unavailable: list[str] = []
    unavailable_detail: list[dict[str, Any]] = []
    if primary in {"pb", "price"} and dna in _BALANCE_SHEET_DNA | {"reit", "invit"}:
        if not health["has_book_value"] and instrument_type == "EQUITY":
            unavailable.append(primary)
            unavailable_detail.append(
                _metric_entry(
                    primary,
                    state="Unavailable",
                    reason="Book value / shareholders' equity unavailable.",
                    confidence="LOW",
                )
            )
            if status not in {"ETF", "REIT", "INVIT", "LOSS_MAKING"}:
                status = "INSUFFICIENT_DATA"
                confidence = "LOW"
                reason_codes = list(dict.fromkeys([*reason_codes, "MISSING_BOOK_VALUE"]))
                reason = "Primary Price-to-Book model unavailable — shareholders' equity missing."
    if primary in {"ev_sales", "ps"} and not health["has_revenue"]:
        unavailable.append(primary)
        unavailable_detail.append(
            _metric_entry(
                primary,
                state="Unavailable",
                reason="Revenue unavailable for sales-based valuation.",
                confidence="LOW",
            )
        )
        if status == "LOSS_MAKING":
            status = "INSUFFICIENT_DATA"
            confidence = "LOW"
    if primary == "ev_ebitda" and health["ebitda"] is None:
        unavailable.append(primary)
        unavailable_detail.append(
            _metric_entry(
                primary,
                state="Unavailable",
                reason="EBITDA unavailable for EV/EBITDA.",
                confidence="LOW",
            )
        )
        if status == "VALID":
            status = "INSUFFICIENT_DATA"
            confidence = "LOW"
            reason_codes = list(dict.fromkeys([*reason_codes, "MISSING_EBITDA"]))

    if coverage["coverage"] == "NONE" and status == "VALID":
        status = "INSUFFICIENT_DATA"
        confidence = "LOW"
        reason_codes = list(dict.fromkeys([*reason_codes, "NO_COVERAGE"]))

    # Deduplicate lists; primary never listed as supporting/hidden.
    supporting = [m for m in dict.fromkeys(supporting) if m != primary and m not in hidden]
    hidden = [m for m in dict.fromkeys(hidden) if m != primary]
    unavailable = [m for m in dict.fromkeys(unavailable)]

    # Per-metric applicability map
    metrics: dict[str, dict[str, Any]] = {}
    for m in supporting:
        metrics[m] = _metric_entry(
            m,
            state="Applicable",
            reason=f"Supporting metric for {_model(primary)} valuation framework.",
            confidence=confidence,
            source="sector_lens+vpae",
        )
    for m in hidden:
        why = _hidden_reason(m, dna=dna, instrument_type=instrument_type, health=health)
        metrics[m] = _metric_entry(m, state="Hidden", reason=why, confidence="HIGH", source="vpae")
    for detail in unavailable_detail:
        metrics[detail["metric"]] = detail
    metrics[primary] = _metric_entry(
        primary,
        state="Applicable" if primary not in unavailable else "Unavailable",
        reason=reason,
        confidence=confidence,
        source="vpae",
    )

    # Insurance preferred model label even when metric key remains pb.
    primary_model = _model(primary)
    if dna == "insurance" and status == "INSURANCE_MODEL":
        primary_model = "PRICE_TO_EMBEDDED_VALUE"
    if instrument_type in {"REIT", "INVIT"}:
        primary_model = "PRICE_TO_NAV"
    if instrument_type in {"ETF", "COMMODITY_ETF", "MUTUAL_FUND"}:
        primary_model = "NAV"

    dqiv = _dqiv_validate(
        primary=primary,
        supporting=supporting,
        hidden=hidden,
        dna=dna,
        instrument_type=instrument_type,
        health=health,
        metrics=metrics,
        reason=reason,
        confidence=confidence,
    )

    return {
        "ok": True,
        "symbol": ticker,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "company": {
            "name": company_name,
            "sector": sector,
            "industry": identity["industry"],
            "industry_dna": dna,
            "business_type": identity.get("business_type"),
            "instrument_type": instrument_type,
        },
        "primary_model": primary_model,
        "primary_metric": primary,
        "supporting_models": [_model(m) for m in supporting],
        "supporting_metrics": supporting,
        "hidden_models": [_model(m) for m in hidden],
        "hidden_metrics": hidden,
        "unavailable_models": [_model(m) for m in unavailable],
        "unavailable_metrics": unavailable,
        "status": status,
        "reason": reason,
        "reason_codes": reason_codes,
        "confidence": confidence,
        "coverage": coverage["coverage"],
        "coverage_detail": coverage,
        "financial_health": {
            "positive_earnings": health["positive_earnings"],
            "negative_earnings": health["negative_earnings"],
            "positive_ebitda": health["positive_ebitda"],
            "has_book_value": health["has_book_value"],
            "has_revenue": health["has_revenue"],
            "missing_fields": health["missing_fields"],
            "observed_multiples": {
                "pe": health.get("pe"),
                "pb": health.get("pb"),
                "ev_ebitda": health.get("ev_ebitda"),
            },
        },
        "metrics": metrics,
        "lens_baseline": {
            "industry_dna": dna,
            "primary_metric": lens.get("primary_metric"),
            "supporting_metrics": lens.get("supporting_metrics"),
            "suppressed_metrics": lens.get("suppressed_metrics"),
            "rationale": lens.get("rationale"),
        },
        "instrument": instrument,
        "identity_source": identity.get("source"),
        "dqiv": dqiv,
        "provenance": {
            "engine": ENGINE_CODE,
            "version": VERSION,
            "baseline": "valuation_terminal.sector_lens",
            "instrument_source": instrument.get("source"),
            "identity_source": identity.get("source"),
        },
    }


def _hidden_reason(
    metric: str,
    *,
    dna: Optional[str],
    instrument_type: str,
    health: dict[str, Any],
) -> str:
    if metric == "pe" and health.get("negative_earnings"):
        return (
            "Negative trailing earnings. Price-to-Earnings is not meaningful; "
            "primary valuation model uses a sales- or book-based framework instead."
        )
    if metric in {"ev_ebitda", "ev_sales", "ps"} and dna in _FINANCIAL_DNA:
        return (
            "Enterprise-value multiples are not meaningful for deposit-taking or "
            "regulated financial institutions."
        )
    if instrument_type in {"ETF", "COMMODITY_ETF", "MUTUAL_FUND", "INDEX"}:
        return f"Company valuation multiples are not applicable to {instrument_type} instruments."
    if instrument_type in {"REIT", "INVIT"} and metric == "pe":
        return f"{instrument_type} vehicles are valued on Price/NAV, not P/E."
    if metric == "pb" and dna in {"it_services", "software", "internet_platforms"}:
        return "Asset-light technology businesses are not primarily valued on book equity."
    return f"{_model(metric)} is suppressed for this business model ({dna or 'unknown'})."


def _dqiv_validate(
    *,
    primary: str,
    supporting: list[str],
    hidden: list[str],
    dna: Optional[str],
    instrument_type: str,
    health: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
    reason: str,
    confidence: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if not primary:
        errors.append("missing_primary_model")
    if not reason:
        errors.append("missing_explanation")
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        errors.append("missing_confidence")
    if primary in hidden:
        errors.append("primary_also_hidden")
    if "pe" not in hidden and health.get("negative_earnings") and dna not in _BALANCE_SHEET_DNA:
        # Loss-making non-financial still showing PE as applicable = policy bug.
        pe_state = (metrics.get("pe") or {}).get("status")
        if pe_state == "Applicable":
            errors.append("loss_making_pe_applicable")
    if dna in _FINANCIAL_DNA and primary in {"ev_ebitda", "ev_sales"}:
        errors.append("financial_primary_uses_ev")
    if instrument_type in {"ETF", "COMMODITY_ETF"} and primary in {"pe", "pb", "ev_ebitda"}:
        errors.append("etf_equity_primary")
    if health.get("negative_earnings") and primary == "pe":
        errors.append("negative_denominator_pe_primary")

    for m, entry in metrics.items():
        if entry.get("status") == "Hidden" and not entry.get("reason"):
            errors.append(f"hidden_without_reason:{m}")

    pe_val = health.get("pe")
    if pe_val is not None and pe_val > EXTREME_PE:
        warnings.append(f"extreme_pe:{pe_val}")

    ok = not errors
    return {
        "ok": ok,
        "status": "ok" if ok and not warnings else ("warn" if ok else "fail"),
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "has_primary": bool(primary),
            "has_explanation": bool(reason),
            "has_confidence": confidence in {"HIGH", "MEDIUM", "LOW"},
            "hidden_explained": all(
                (metrics.get(m) or {}).get("reason") for m in hidden
            ),
            "business_match": "financial_primary_uses_ev" not in errors,
            "instrument_match": "etf_equity_primary" not in errors,
        },
    }


def is_meaningful(metric: str, policy: dict[str, Any]) -> bool:
    """Whether UVE / UI may display this metric given a VPAE policy."""
    if not policy or not policy.get("ok"):
        return True
    if metric in (policy.get("hidden_metrics") or []):
        return False
    if metric in (policy.get("unavailable_metrics") or []):
        return False
    entry = (policy.get("metrics") or {}).get(metric) or {}
    if entry.get("status") in {"Hidden", "Suppressed"}:
        return False
    return True


def applicable_metrics(policy: dict[str, Any]) -> list[str]:
    if not policy or not policy.get("ok"):
        return []
    out = []
    primary = policy.get("primary_metric")
    if primary and primary not in (policy.get("unavailable_metrics") or []):
        out.append(primary)
    for m in policy.get("supporting_metrics") or []:
        if m not in out and m not in (policy.get("hidden_metrics") or []):
            out.append(m)
    return out
