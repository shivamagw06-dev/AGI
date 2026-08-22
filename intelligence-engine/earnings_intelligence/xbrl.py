"""IND-AS / Integrated Filing XBRL downloader + normalizer."""

from __future__ import annotations

import re
from typing import Any

from institutional_warehouse import units as warehouse_units
from institutional_warehouse import xbrl_units as xu
from ownership_intelligence.dates import parse_nse_date

# Map local XBRL concept → canonical pack field (OneD = period facts)
INCOME_MAP = {
    "RevenueFromOperations": "revenue_from_operations",
    "OtherIncome": "other_income",
    "Income": "total_income",
    "Expenses": "expenses",
    "EmployeeBenefitExpense": "employee_benefit_expense",
    "FinanceCosts": "finance_costs",
    "DepreciationDepletionAndAmortisationExpense": "depreciation",
    "ProfitBeforeExceptionalItemsAndTax": "pbt_before_exceptional",
    "ProfitBeforeTax": "pbt",
    # Banking / older IND-AS aliases
    "ProfitLossFromOrdinaryActivitiesBeforeTax": "pbt",
    "OperatingProfitBeforeProvisionAndContingencies": "ebit",
    "TaxExpense": "tax_expense",
    "CurrentTax": "current_tax",
    "DeferredTax": "deferred_tax",
    "ProfitLossForPeriod": "pat",
    "ProfitLossForThePeriod": "pat",
    "ProfitLossFromOrdinaryActivitiesAfterTax": "pat",
    "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates": "pat",
    "ProfitLossForPeriodFromContinuingOperations": "pat_continuing",
    "ProfitOrLossAttributableToOwnersOfParent": "pat_owners",
    "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "eps_basic",
    "BasicEarningsLossPerShareFromContinuingOperations": "eps_basic_cont",
    # Banking XBRL EPS aliases
    "BasicEarningsPerShareAfterExtraordinaryItems": "eps_basic",
    "BasicEarningsPerShareBeforeExtraordinaryItems": "eps_basic",
    "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "eps_diluted",
    "DilutedEarningsLossPerShareFromContinuingOperations": "eps_diluted_cont",
    "DilutedEarningsPerShareAfterExtraordinaryItems": "eps_diluted",
    "DilutedEarningsPerShareBeforeExtraordinaryItems": "eps_diluted",
}

BALANCE_MAP = {
    "Assets": "total_assets",
    "CurrentAssets": "current_assets",
    "NonCurrentAssets": "non_current_assets",
    "CashAndCashEquivalents": "cash",
    "Equity": "total_equity",
    # Note: bank "Capital" is ambiguous (share capital vs capital+liabilities) — do not map to equity.
    "CapitalAndLiabilities": "equity_and_liabilities",
    "EquityAndLiabilities": "equity_and_liabilities",
    "EquityShareCapital": "equity_share_capital",
    "PaidUpValueOfEquityShareCapital": "equity_share_capital",
    "FaceValueOfEquityShareCapital": "face_value",
    "EquityAttributableToOwnersOfParent": "equity_owners",
    "OtherEquity": "reserves",
    "ReservesAndSurplus": "reserves",
    "ReserveExcludingRevaluationReserves": "reserves",
    "Liabilities": "total_liabilities",
    "CurrentLiabilities": "current_liabilities",
    "NonCurrentLiabilities": "non_current_liabilities",
    "Borrowings": "borrowings",
    "CurrentBorrowings": "current_borrowings",
    "NonCurrentBorrowings": "non_current_borrowings",
    "Deposits": "deposits",
}

CASHFLOW_MAP = {
    "CashFlowsFromUsedInOperatingActivities": "operating_cash_flow",
    "CashFlowsFromUsedInInvestingActivities": "investing_cash_flow",
    "CashFlowsFromUsedInFinancingActivities": "financing_cash_flow",
    "IncreaseDecreaseInCashAndCashEquivalents": "net_change_in_cash",
    "CashAndCashEquivalentsCashFlowStatement": "cash_end",
}

_NON_AGGREGATE_DESTINATIONS = {
    "eps_basic", "eps_basic_cont", "eps_diluted", "eps_diluted_cont",
    "face_value", "shares_outstanding",
}
_PER_SHARE_CONCEPTS = {
    source
    for mapping in (INCOME_MAP, BALANCE_MAP)
    for source, destination in mapping.items()
    if destination in {
        "eps_basic", "eps_basic_cont", "eps_diluted", "eps_diluted_cont",
        "face_value",
    }
}
_AGGREGATE_CONCEPTS = {
    source
    for mapping in (INCOME_MAP, BALANCE_MAP, CASHFLOW_MAP)
    for source, destination in mapping.items()
    if destination not in _NON_AGGREGATE_DESTINATIONS
} | {
    "SegmentRevenue", "SegmentRevenueFromOperations", "SegmentProfitBeforeTax",
    "SegmentProfitLossBeforeTaxAndFinanceCosts", "SegmentAssets",
    "SegmentLiabilities", "SegmentFinanceCosts",
}


def download_xbrl(url: str, *, opener=None) -> bytes:
    from live_data.collectors.base import http_get, nse_session_opener

    op = opener or nse_session_opener()
    return http_get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/xml,text/xml,*/*",
            "Referer": "https://www.nseindia.com/",
        },
        timeout=60,
        opener=op,
    )


def _num(raw: str) -> float | None:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _attribute(attrs: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}\s*=\s*["\']([^"\']*)["\']', attrs or "")
    return match.group(1) if match else None


def _record_unit_outcome(
    audit: dict[str, Any],
    *,
    resolved: bool,
    reason: str,
    category: str = "money",
) -> None:
    key = f"{'resolved' if resolved else 'rejected'}_{category}_facts"
    audit[key] = int(audit.get(key) or 0) + 1
    reasons = audit.setdefault("reasons", {})
    reasons[reason] = int(reasons.get(reason) or 0) + 1


def _facts_for_context(
    text: str,
    ctx: str,
    *,
    unit_defs: dict[str, dict[str, Any]] | None = None,
    unit_audit: dict[str, Any] | None = None,
    inline: bool = False,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for m in re.finditer(rf"<([A-Za-z0-9_:-]+)([^>]*)>", text):
        tag, attrs = m.group(1), m.group(2)
        if _attribute(attrs, "contextRef") != ctx:
            continue
        local = tag.split(":")[-1]
        rest = text[m.end() : m.end() + 64]
        vm = re.match(r"\s*([-+]?[0-9][0-9,]*\.?[0-9]*)", rest)
        if not vm:
            continue
        raw_value = vm.group(1).replace(",", "")
        val = _num(raw_value)
        if val is None:
            continue
        if unit_defs is not None and local in _PER_SHARE_CONCEPTS:
            unit_ref = _attribute(attrs, "unitRef")
            unit = unit_defs.get(str(unit_ref)) if unit_ref else None
            scale = _attribute(attrs, "scale")
            if inline or scale not in (None, ""):
                reason = "inline_xbrl_scale_not_supported"
            elif not unit_ref:
                reason = "missing_unitRef"
            elif unit is None:
                reason = f"unitRef_not_declared:{unit_ref}"
            elif (
                unit.get("kind") != xu.COMPOUND
                or unit.get("measures") != ["iso4217:INR", "xbrli:shares"]
            ):
                reason = "per_share_unit_not_declared"
            else:
                reason = None
            if reason is not None:
                if unit_audit is not None:
                    _record_unit_outcome(
                        unit_audit,
                        resolved=False,
                        reason=reason,
                        category="per_share",
                    )
                continue
            if unit_audit is not None:
                _record_unit_outcome(
                    unit_audit,
                    resolved=True,
                    reason="declared_per_share",
                    category="per_share",
                )
        elif unit_defs is not None and local in _AGGREGATE_CONCEPTS:
            resolved = xu.resolve(
                {
                    "unitRef": _attribute(attrs, "unitRef"),
                    "decimals": _attribute(attrs, "decimals"),
                    "scale": _attribute(attrs, "scale"),
                    "raw_value": raw_value,
                },
                unit_defs,
            )
            if inline and resolved["usable_as_money"]:
                resolved = {
                    **resolved,
                    "usable_as_money": False,
                    "normalised_value": None,
                    "reason": "inline_xbrl_scale_not_supported",
                }
            if not resolved["usable_as_money"]:
                if unit_audit is not None:
                    _record_unit_outcome(
                        unit_audit,
                        resolved=False,
                        reason=str(resolved.get("reason") or "unit_unresolved"),
                    )
                continue
            val = float(resolved["normalised_value"])
            if unit_audit is not None:
                _record_unit_outcome(unit_audit, resolved=True, reason="declared")
        # Keep first (or prefer finite)
        if local not in out:
            out[local] = val
    return out


def _map_block(facts: dict[str, float], mapping: dict[str, str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {v: None for v in mapping.values()}
    for src, dest in mapping.items():
        if src in facts and out.get(dest) is None:
            out[dest] = facts[src]
    # Prefer continuing ops EPS when combined missing
    if out.get("eps_basic") is None and out.get("eps_basic_cont") is not None:
        out["eps_basic"] = out["eps_basic_cont"]
    if out.get("eps_diluted") is None and out.get("eps_diluted_cont") is not None:
        out["eps_diluted"] = out["eps_diluted_cont"]
    if out.get("pat") is None and out.get("pat_continuing") is not None:
        out["pat"] = out["pat_continuing"]
    if out.get("pat_owners") is None and out.get("pat") is not None:
        out["pat_owners"] = out["pat"]
    return out


def _derive_income(income: dict[str, Any]) -> dict[str, Any]:
    rev = income.get("revenue_from_operations")
    other = income.get("other_income")
    if income.get("total_income") is None and rev is not None:
        income["total_income"] = round(float(rev) + float(other or 0.0), 2)
    dep = income.get("depreciation")
    fin = income.get("finance_costs")
    pbt = income.get("pbt")
    # EBIT ≈ PBT + finance costs (soft)
    if income.get("ebit") is None and pbt is not None:
        income["ebit"] = round(float(pbt) + float(fin or 0.0), 2)
    # EBITDA ≈ EBIT + D&A
    if income.get("ebitda") is None and income.get("ebit") is not None:
        income["ebitda"] = round(float(income["ebit"]) + float(dep or 0.0), 2)
    return income


def _derive_balance(bal: dict[str, Any]) -> dict[str, Any]:
    ca = bal.get("current_assets")
    cl = bal.get("current_liabilities")
    if bal.get("working_capital") is None and ca is not None and cl is not None:
        bal["working_capital"] = round(float(ca) - float(cl), 2)
    # Debt soft sum
    debt_parts = [bal.get("borrowings"), bal.get("current_borrowings"), bal.get("non_current_borrowings")]
    nums = [float(x) for x in debt_parts if x is not None]
    if bal.get("total_debt") is None and nums:
        # Avoid double-count if both aggregate and split present
        if bal.get("borrowings") is not None:
            bal["total_debt"] = float(bal["borrowings"])
        else:
            bal["total_debt"] = round(sum(nums), 2)
    # Banking: reconstruct book equity from paid-up capital + reserves
    esc = bal.get("equity_share_capital")
    reserves = bal.get("reserves")
    if bal.get("total_equity") is None and esc is not None and reserves is not None:
        bal["total_equity"] = round(float(esc) + float(reserves), 2)
    if bal.get("total_equity") is None and bal.get("equity_owners") is not None:
        bal["total_equity"] = bal["equity_owners"]
    # Reject mis-mapped "Capital" share-capital-as-equity when assets dwarf equity
    assets = bal.get("total_assets")
    te = bal.get("total_equity")
    if (
        te is not None
        and assets not in (None, 0)
        and float(te) / float(assets) < 0.005
        and esc is not None
        and reserves is not None
    ):
        bal["total_equity"] = round(float(esc) + float(reserves), 2)
    if bal.get("reserves") is None and bal.get("total_equity") is not None and bal.get("equity_share_capital") is not None:
        bal["reserves"] = round(float(bal["total_equity"]) - float(bal["equity_share_capital"]), 2)
    # Paid-up capital is canonical INR million; face value is declared INR/share.
    face = bal.get("face_value")
    if bal.get("shares_outstanding") is None and esc not in (None, 0) and face not in (None, 0):
        try:
            bal["shares_outstanding"] = round(
                float(esc) * 1_000_000.0 / float(face),
                2,
            )
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    return bal


def _derive_cashflow(cf: dict[str, Any]) -> dict[str, Any]:
    ocf = cf.get("operating_cash_flow")
    icf = cf.get("investing_cash_flow")
    # Soft FCF = OCF + Investing (investing usually negative / includes capex)
    if cf.get("free_cash_flow") is None and ocf is not None and icf is not None:
        cf["free_cash_flow"] = round(float(ocf) + float(icf), 2)
    # Capex proxy: negative investing outflow magnitude when only one investing line
    if cf.get("capex") is None and icf is not None and float(icf) < 0:
        cf["capex"] = round(abs(float(icf)), 2)
    return cf


def _parse_segments(
    text: str,
    *,
    unit_defs: dict[str, dict[str, Any]] | None = None,
    unit_audit: dict[str, Any] | None = None,
    inline: bool = False,
) -> list[dict[str, Any]]:
    """Extract reportable segment rows when present."""
    # Pair DescriptionOfReportableSegment with nearby SegmentRevenue in same typed context
    segs: list[dict[str, Any]] = []
    # Context ids that look like segment detail
    for m in re.finditer(
        r'DescriptionOfReportableSegment[^>]*contextRef="([^"]+)"[^>]*>([^<]+)<',
        text,
        re.I,
    ):
        ctx, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if not name:
            continue
        facts = _facts_for_context(
            text, ctx, unit_defs=unit_defs, unit_audit=unit_audit, inline=inline,
        )
        # Also try sibling OneD-less segment contexts — often same numeric on OneD with axis
        row = {
            "name": name,
            "revenue": facts.get("SegmentRevenue") or facts.get("SegmentRevenueFromOperations"),
            "profit_before_tax": facts.get("SegmentProfitBeforeTax")
            or facts.get("SegmentProfitLossBeforeTaxAndFinanceCosts"),
            "assets": facts.get("SegmentAssets"),
            "liabilities": facts.get("SegmentLiabilities"),
            "finance_costs": facts.get("SegmentFinanceCosts"),
            "context": ctx,
        }
        if any(row.get(k) is not None for k in ("revenue", "profit_before_tax", "assets")):
            segs.append(row)
    # Dedupe by name keep first
    seen: set[str] = set()
    uniq = []
    for s in segs:
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        uniq.append(s)
    return uniq


def _merge_facts(*fact_maps: dict[str, float]) -> dict[str, float]:
    """Left-to-right fill — first non-null wins."""
    out: dict[str, float] = {}
    for fmap in fact_maps:
        for k, v in (fmap or {}).items():
            if k not in out:
                out[k] = v
    return out


def parse_financial_xbrl(raw: bytes | str) -> dict[str, Any]:
    """Normalize financial XBRL into income / balance / cashflow / segments."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)

    unit_defs = xu.parse_units(text)
    inline = xu.is_inline_xbrl(text)
    unit_audit: dict[str, Any] = {
        "resolved_money_facts": 0,
        "rejected_money_facts": 0,
        "reasons": {},
    }

    # OneD = duration (P&L / period CF); OneI = instant (balance sheet);
    # FourD = YTD / annual cumulative on many IND-AS filings.
    fact_args = {"unit_defs": unit_defs, "unit_audit": unit_audit, "inline": inline}
    one = _facts_for_context(text, "OneD", **fact_args)
    one_i = _facts_for_context(text, "OneI", **fact_args)
    four = _facts_for_context(text, "FourD", **fact_args)
    four_i = _facts_for_context(text, "FourI", **fact_args)

    # Re-map income preferring OneD (period) explicitly
    income = _derive_income(_map_block(one if one else four, INCOME_MAP))
    ytd_income = _derive_income(_map_block(four, INCOME_MAP)) if four else {}
    # Balance sheet is point-in-time → instant contexts
    balance = _derive_balance(_map_block(_merge_facts(one_i, four_i, one, four), BALANCE_MAP))
    # Cash flow: period on OneD; annual totals often only on FourD
    cashflow = _derive_cashflow(_map_block(_merge_facts(one, four), CASHFLOW_MAP))
    segments = _parse_segments(text, **fact_args)

    # Instant date if present
    as_of = None
    m = re.search(r"<xbrli:instant>([^<]+)</xbrli:instant>", text, re.I)
    if m:
        as_of = parse_nse_date(m.group(1))

    has_income = income.get("revenue_from_operations") is not None or income.get("pat") is not None
    has_balance = balance.get("total_assets") is not None or balance.get("total_equity") is not None
    has_cf = cashflow.get("operating_cash_flow") is not None

    return {
        "ok": bool(has_income or has_balance or has_cf),
        "as_of": as_of,
        "income_statement": income,
        "income_ytd": ytd_income if any(v is not None for v in ytd_income.values()) else None,
        "balance_sheet": balance,
        "cash_flow": cashflow,
        "segments": segments,
        "has_income": has_income,
        "has_balance": has_balance,
        "has_cash_flow": has_cf,
        "has_segments": bool(segments),
        "source": "nse_financial_xbrl",
        "provider": "nse_india",
        "parser_path": "nse_xbrl_fact",
        "units_in": "inr_million" if unit_audit["resolved_money_facts"] else None,
        "unit_resolution": {
            **unit_audit,
            "method": "declared_per_fact",
            "canonical_money_unit": "inr_million",
            "inline_xbrl": inline,
            "decimals_used_as_scale": False,
        },
        "concepts_present": sorted(one.keys())[:80],
    }


def _fse_ingest_xbrl_bytes(
    filing: dict[str, Any],
    raw: bytes,
    *,
    source_url: str | None,
) -> dict[str, Any] | None:
    """FSE-02.1 adapter: submit XBRL bytes through canonical ingest (no parse call)."""
    try:
        from financial_statements_engine.collection.flags import canonical_ingest_enabled
        from financial_statements_engine.collection.ingest import ingest
    except Exception:  # pragma: no cover
        return None
    if not canonical_ingest_enabled():
        return None
    ticker = str(filing.get("ticker") or filing.get("symbol") or filing.get("entity") or "").upper().strip()
    if not ticker:
        return None
    period_end = filing.get("period_end") or filing.get("end_date") or filing.get("to_date")
    freq = str(filing.get("frequency") or filing.get("period_type") or "").lower()
    if "annual" in freq or freq in {"yearly", "year"}:
        period_type = "annual"
    elif "quarter" in freq or freq in {"q", "qtr"}:
        period_type = "quarterly"
    else:
        period_type = filing.get("period_type") or "quarterly"
    try:
        return ingest(
            ticker=ticker,
            content=raw,
            source=str(filing.get("source") or "nse_financial_xbrl"),
            source_url=source_url,
            document_type="xbrl",
            period_type=str(period_type),
            period_end=str(period_end)[:10] if period_end else None,
            filing_type=str(period_type),
            collector="earnings_intelligence",
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "action": "failed", "error": str(exc)[:160]}


def enrich_filing_with_xbrl(
    filing: dict[str, Any],
    *,
    opener=None,
    injected_xbrl: bytes | str | None = None,
) -> dict[str, Any]:
    out = dict(filing)
    url = filing.get("xbrl_url")
    raw_bytes: bytes | None = None
    try:
        if injected_xbrl is not None:
            raw_bytes = injected_xbrl if isinstance(injected_xbrl, (bytes, bytearray)) else str(injected_xbrl).encode("utf-8")
            detail = parse_financial_xbrl(injected_xbrl)
            out["xbrl_mode"] = "injected"
            out["xbrl_bytes"] = len(raw_bytes)
        elif url:
            raw_bytes = download_xbrl(str(url), opener=opener)
            detail = parse_financial_xbrl(raw_bytes)
            out["xbrl_mode"] = "live"
            out["xbrl_bytes"] = len(raw_bytes)
        else:
            out["xbrl_error"] = "xbrl_url_missing"
            return out
    except Exception as exc:  # noqa: BLE001
        out["xbrl_error"] = f"{type(exc).__name__}:{str(exc)[:160]}"
        return out

    if raw_bytes is not None:
        fse = _fse_ingest_xbrl_bytes(out, bytes(raw_bytes), source_url=str(url) if url else None)
        if fse is not None:
            out["fse_ingest"] = {
                "ok": fse.get("ok"),
                "action": fse.get("action"),
                "evidence_id": fse.get("evidence_id"),
                "event_emitted": fse.get("event_emitted"),
                "content_sha256": fse.get("content_sha256"),
            }
            if fse.get("action") in {"stored", "restatement_candidate", "duplicate_skipped"}:
                out["fse_xbrl_ingested"] = True

    out["statements"] = {
        "income_statement": detail.get("income_statement"),
        "income_ytd": detail.get("income_ytd"),
        "balance_sheet": detail.get("balance_sheet"),
        "cash_flow": detail.get("cash_flow"),
        "segments": detail.get("segments") or [],
    }
    out["xbrl_ok"] = bool(detail.get("ok"))
    out["has_income"] = detail.get("has_income")
    out["has_balance"] = detail.get("has_balance")
    out["has_cash_flow"] = detail.get("has_cash_flow")
    out["has_segments"] = detail.get("has_segments")
    out["detail_source"] = filing.get("source")
    out["provider"] = detail.get("provider")
    out["parser_path"] = detail.get("parser_path")
    out["units_in"] = detail.get("units_in")
    out["unit_resolution"] = detail.get("unit_resolution")
    # Soft fill from integrated summary when XBRL thin
    summary = filing.get("raw_summary") or {}
    inc = out["statements"]["income_statement"] or {}
    if inc.get("revenue_from_operations") is None and summary.get("income") not in (None, ""):
        summary_unit_raw = (
            summary.get("units_in") or summary.get("unit") or summary.get("unit_of_measure")
        )
        summary_unit = warehouse_units.canonical_unit_name(summary_unit_raw)
        if summary_unit is None:
            out["integrated_summary_skipped"] = "unit_not_declared"
        else:
            try:
                inc["revenue_from_operations"] = (
                    float(summary["income"])
                    * warehouse_units.SCALE_TO_MILLION[summary_unit]
                )
            except (TypeError, ValueError):
                out["integrated_summary_skipped"] = "income_not_numeric"
            else:
                previous_path = out.get("parser_path") if out.get("units_in") else None
                out["provider"] = "nse_india"
                out["parser_path"] = (
                    f"{previous_path}+integrated_summary_declared"
                    if previous_path else "integrated_summary_declared"
                )
                out["units_in"] = "inr_million"
                out["integrated_summary_reported_unit"] = summary_unit
                out["scaled_from_integrated_lakhs"] = summary_unit in {"lakh", "inr_lakh"}
                out["statements"]["income_statement"] = _derive_income(inc)
                out["has_income"] = True
    return out
