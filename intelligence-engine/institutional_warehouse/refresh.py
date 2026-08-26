"""Daily refresh engine.

Runs the institutional pipeline in order, appending snapshots and never
overwriting history:

    Groww -> Yahoo -> Capital IQ -> NSE -> CGL -> Knowledge Factory
          -> Financial Statements -> Validation -> Recalculate -> Publish

Every stage is independent: a dead collector degrades one stage, it does not
stall the refresh. Each stage reports what it read and what it wrote.
"""

from __future__ import annotations

import csv
import json
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from institutional_warehouse import audit, db, gateway, store, validation
from institutional_warehouse.formulas import recalculate
from institutional_warehouse.values import now_iso, to_date, to_number, today_iso

BHAV_FILE_RE = re.compile(r"sec_bhavdata_full_(\d{2})(\d{2})(\d{4})\.csv$", re.IGNORECASE)
MAX_BHAV_FILES = 400


def _ok(stage: str, **payload: Any) -> dict[str, Any]:
    return {"stage": stage, "ok": True, **payload}


def _skip(stage: str, reason: str, **payload: Any) -> dict[str, Any]:
    return {"stage": stage, "ok": True, "skipped": True, "reason": reason, **payload}


def _fail(stage: str, error: str) -> dict[str, Any]:
    return {"stage": stage, "ok": False, "error": error}


# --------------------------------------------------------------------------
# Stage: Groww (intraday quotes)
# --------------------------------------------------------------------------


def stage_groww(*, actor: str) -> dict[str, Any]:
    """Live Groww prices are securely collected by the finance backend.

    The backend owns the credential and sends bounded, candidate-only price
    snapshots into this warehouse.  The engine must not duplicate the token or
    perform a universe scan during a refresh.
    """
    return _skip("groww", "delegated_to_finance_backend", actor=actor)


# --------------------------------------------------------------------------
# Stage: Yahoo (valuation terminal multiples)
# --------------------------------------------------------------------------


def stage_yahoo(*, actor: str, limit: Optional[int] = None) -> dict[str, Any]:
    try:
        from valuation_terminal.store import all_rows
    except Exception as exc:
        return _fail("yahoo", f"valuation_terminal_unavailable:{exc}")

    rows = all_rows() or {}
    if not rows:
        return _skip("yahoo", "valuation_terminal_empty")

    stamp = today_iso()
    masters: list[dict[str, Any]] = []
    prices: list[dict[str, Any]] = []
    valuations: list[dict[str, Any]] = []

    for index, (ticker, row) in enumerate(rows.items()):
        if limit and index >= limit:
            break
        symbol = str(ticker).strip().upper()
        if not symbol:
            continue
        masters.append(
            {
                "company_id": symbol,
                "symbol": symbol,
                "company_name": row.get("company_name") or symbol,
                "sector": row.get("primary_sector"),
                "industry": row.get("primary_industry") or row.get("nse_industry"),
                "industry_dna": row.get("industry_dna"),
                "business_type": row.get("business_type"),
                "exchange": "NSE",
                "currency": "INR",
                "country": "India",
                "market_status": "listed",
                "active": True,
                "source": "yahoo_finance",
            }
        )
        price = to_number(row.get("price"))
        if price is not None:
            prices.append(
                {
                    "symbol": symbol,
                    "date": stamp,
                    "close": price,
                    "market_cap": to_number(row.get("market_cap")),
                    "source": "yahoo_finance",
                }
            )
        valuations.append(
            {
                "date": stamp,
                "symbol": symbol,
                "cmp": price,
                "market_cap": to_number(row.get("market_cap")),
                "pe": to_number(row.get("pe")),
                "forward_pe": to_number(row.get("forward_pe")),
                "pb": to_number(row.get("pb")),
                "ev_ebitda": to_number(row.get("ev_ebitda")),
                "ev_sales": to_number(row.get("ev_sales")),
                "price_sales": to_number(row.get("ps")),
                "dividend_yield": to_number(row.get("dividend_yield")),
                "source": "yahoo_finance",
            }
        )

    master_result = gateway.write("company_master", masters, source="yahoo_finance", actor=actor,
                                 reason="refresh:yahoo")
    price_result = gateway.write("daily_market_history", prices, source="yahoo_finance", actor=actor,
                                reason="refresh:yahoo")
    # Valuation is not sourced from Yahoo. Ratios come from Upstox key-ratios
    # and from warehouse_reconstruction over the Capital IQ workbook, which is
    # the annual record. Yahoo kept writing historical_valuation because this
    # call predates that decision, not because it was chosen.
    #
    # The prices and company master above still come from Yahoo, which is a
    # separate question from valuation and is left alone here.
    valuation_result = {"ok": True, "skipped": "valuation_not_sourced_from_yahoo",
                        "candidates": len(valuations), "written": 0}
    return _ok(
        "yahoo",
        companies=len(masters),
        company_master=master_result,
        daily_market_history=price_result,
        historical_valuation=valuation_result,
    )


# --------------------------------------------------------------------------
# Stage: Capital IQ (institutional knowledge tables + consensus)
# --------------------------------------------------------------------------


def _capiq_current(table: dict[str, Any], field: str) -> Any:
    facts = (table or {}).get(field)
    if isinstance(facts, list) and facts:
        current = [f for f in facts if f.get("current")]
        return (current or facts)[-1].get("value")
    if isinstance(facts, dict):
        return facts.get("value")
    return None


def stage_capital_iq(*, actor: str, limit: Optional[int] = None) -> dict[str, Any]:
    written = {"company_master": None, "financials_annual": None, "consensus": None}
    try:
        from institutional_knowledge_tables.store import get_table, list_companies
    except Exception as exc:
        return _fail("capital_iq", f"ikt_unavailable:{exc}")

    tickers = list_companies() or []
    if limit:
        tickers = tickers[:limit]

    masters: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    for ticker in tickers:
        symbol = str(ticker).strip().upper()
        try:
            master = get_table(ticker, "company_master") or {}
            financials = get_table(ticker, "financial_statements") or {}
        except Exception:
            continue
        fields = master.get("fields") if isinstance(master.get("fields"), dict) else master
        fin_fields = financials.get("fields") if isinstance(financials.get("fields"), dict) else financials

        name = _capiq_current(fields, "company_name")
        if name:
            masters.append(
                {
                    "company_id": symbol,
                    "symbol": symbol,
                    "company_name": name,
                    "legal_name": name,
                    "industry": _capiq_current(fields, "industry"),
                    "country": _capiq_current(fields, "country"),
                    "currency": _capiq_current(fields, "currency"),
                    "isin": _capiq_current(fields, "isin"),
                    "website": _capiq_current(fields, "website"),
                    "market_status": "listed",
                    "active": True,
                    "source": "capital_iq",
                }
            )
        revenue = _capiq_current(fin_fields, "LTM::revenue")
        ebitda = _capiq_current(fin_fields, "LTM::ebitda")
        if revenue is not None or ebitda is not None:
            statements.append(
                {
                    "symbol": symbol,
                    "fiscal_year": "LTM",
                    "revenue": to_number(revenue),
                    "ebitda": to_number(ebitda),
                    "source": "capital_iq",
                    "statement_version": "capiq_ltm",
                }
            )
    written["company_master"] = gateway.write("company_master", masters, source="capital_iq",
                                             actor=actor, reason="refresh:capital_iq")
    written["financials_annual"] = gateway.write("financials_annual", statements, source="capital_iq",
                                                actor=actor, reason="refresh:capital_iq")
    written["consensus"] = _refresh_consensus(actor=actor, limit=limit)
    return _ok("capital_iq", companies=len(tickers), **written)


def _refresh_consensus(*, actor: str, limit: Optional[int] = None) -> dict[str, Any]:
    try:
        from valuation_consensus.store import load_live
    except Exception as exc:
        return {"ok": False, "error": f"valuation_consensus_unavailable:{exc}"}

    payload = load_live() or {}
    rows = payload.get("rows") or {}
    if isinstance(rows, list):
        rows = {str(r.get("ticker") or "").upper(): r for r in rows}
    stamp = to_date(payload.get("updated_at")) or today_iso()

    staged = []
    for index, (ticker, row) in enumerate(rows.items()):
        if limit and index >= limit:
            break
        symbol = str(ticker).strip().upper()
        if not symbol:
            continue
        target = to_number(row.get("target_price"))
        counts = [row.get(k) for k in ("buy_count", "outperform_count", "hold_count", "sell_count")]
        if target is None and not any(to_number(c) for c in counts):
            continue
        staged.append(
            {
                "symbol": symbol,
                "consensus_date": stamp,
                "target_price": target,
                "high_target": to_number(row.get("target_high")),
                "low_target": to_number(row.get("target_low")),
                "buy": to_number(row.get("buy_count")),
                "outperform": to_number(row.get("outperform_count")),
                "hold": to_number(row.get("hold_count")),
                "sell": to_number(row.get("sell_count")),
                "no_opinion": to_number(row.get("no_opinion_count")),
                "source": "capital_iq_consensus",
            }
        )
    return gateway.write("consensus", staged, source="capital_iq_consensus", actor=actor,
                        reason="refresh:consensus")


# --------------------------------------------------------------------------
# Stage: NSE (bhavcopy files collected by the intelligence worker)
# --------------------------------------------------------------------------


def _bhav_files(limit: int = MAX_BHAV_FILES) -> list[tuple[str, Path]]:
    try:
        from live_data.store import store_root
    except Exception:
        return []
    directory = store_root() / "files" / "nse_bhavcopy"
    if not directory.exists():
        return []
    by_date: dict[str, Path] = {}
    for path in directory.glob("*.csv"):
        match = BHAV_FILE_RE.search(path.name)
        if not match:
            continue
        day, month, year = match.groups()
        by_date[f"{year}-{month}-{day}"] = path
    ordered = sorted(by_date.items(), reverse=True)[:limit]
    return list(reversed(ordered))


def _parse_bhav(path: Path, trade_date: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return rows
    reader = csv.DictReader(line for line in text.splitlines())
    for raw in reader:
        record = { (k or "").strip().upper(): (v.strip() if isinstance(v, str) else v)
                   for k, v in raw.items() if k }
        if (record.get("SERIES") or "").upper() not in ("EQ", "BE"):
            continue
        symbol = (record.get("SYMBOL") or "").strip().upper()
        if not symbol:
            continue
        rows.append(
            {
                "symbol": symbol,
                "date": to_date(record.get("DATE1")) or trade_date,
                "open": to_number(record.get("OPEN_PRICE")),
                "high": to_number(record.get("HIGH_PRICE")),
                "low": to_number(record.get("LOW_PRICE")),
                "close": to_number(record.get("CLOSE_PRICE")),
                "adjusted_close": to_number(record.get("CLOSE_PRICE")),
                "vwap": to_number(record.get("AVG_PRICE")),
                "volume": to_number(record.get("TTL_TRD_QNTY")),
                "delivery_pct": to_number(record.get("DELIV_PER")),
                "source": "nse_bhavcopy",
            }
        )
    return rows


def stage_nse(*, actor: str, days: int = 30, symbols: Optional[Iterable[str]] = None) -> dict[str, Any]:
    files = _bhav_files(limit=max(1, int(days)))
    if not files:
        return _skip("nse", "no_bhavcopy_files")
    wanted = {str(s).upper() for s in symbols} if symbols else None

    totals = {"inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    dates: list[str] = []
    traded: set[str] = set()
    for trade_date, path in files:
        rows = _parse_bhav(path, trade_date)
        if wanted:
            rows = [r for r in rows if r["symbol"] in wanted]
        if not rows:
            continue
        result = gateway.write("daily_market_history", rows, source="nse_bhavcopy", actor=actor,
                              reason=f"refresh:nse:{trade_date}", fill_only=True)
        for key in totals:
            totals[key] += int(result.get(key) or 0)
        traded.update(r["symbol"] for r in rows)
        dates.append(trade_date)

    registered = _register_traded_symbols(traded, actor=actor)
    return _ok("nse", files=len(files), trading_days=len(dates), first=dates[0] if dates else None,
               last=dates[-1] if dates else None, registered_companies=registered, **totals)


def _register_traded_symbols(symbols: set[str], *, actor: str) -> int:
    """Put every traded symbol in Company Master.

    The bhavcopy covers the whole exchange while the Yahoo universe covers a
    subset, so without this the registry knows fewer companies than the
    warehouse actually holds prices for. Only genuinely new symbols are written:
    an existing row must never have its real company name overwritten by its
    ticker.
    """
    if not symbols:
        return 0
    known = set(store.entities("company_master"))
    fresh = sorted(symbols - known)
    if not fresh:
        return 0
    rows = [
        {
            "company_id": symbol,
            "symbol": symbol,
            # The ticker is all this source knows. Yahoo and Capital IQ fill in the
            # legal name on their next pass without this stage clobbering it.
            "company_name": symbol,
            "exchange": "NSE",
            "currency": "INR",
            "country": "India",
            "market_status": "listed",
            "active": True,
            "source": "nse_bhavcopy",
        }
        for symbol in fresh
    ]
    result = gateway.write("company_master", rows, source="nse_bhavcopy", actor=actor,
                          reason="refresh:nse:register_traded")
    return int(result.get("inserted") or 0)


def stage_lidi_events(*, actor: str, limit: int = 2000) -> dict[str, Any]:
    """Corporate events collected by LIDI become timeline + corporate action rows."""
    try:
        from live_data.store import store_root
    except Exception as exc:
        return _fail("lidi_events", f"live_data_unavailable:{exc}")

    directory = store_root() / "objects" / "CORPORATE_EVENT"
    if not directory.exists():
        return _skip("lidi_events", "no_corporate_events")

    timeline: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for index, path in enumerate(sorted(directory.glob("*.json"), reverse=True)):
        if index >= limit:
            break
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        symbol = str(payload.get("symbol") or payload.get("ticker") or "").strip().upper()
        event_date = to_date(payload.get("event_date"))
        headline = str(payload.get("headline") or payload.get("event_type") or "").strip()
        if not symbol or not event_date or not headline:
            continue
        details = payload.get("details") or {}
        timeline.append(
            {
                "symbol": symbol,
                "date": event_date,
                "event": headline,
                "results": str(details.get("description") or "") or None,
                "source": str(payload.get("source") or "lidi"),
            }
        )
        kind = _action_kind(headline)
        if kind:
            actions.append(
                {
                    "symbol": symbol,
                    "action_date": event_date,
                    "action_type": kind,
                    "details": str(details.get("description") or headline),
                    "source": str(payload.get("source") or "lidi"),
                }
            )
    ca_result = gateway.write(
        "corporate_actions", actions, source="lidi", actor=actor, reason="refresh:lidi_events",
    )
    hvie_ca = None
    try:
        from historical_valuation_intelligence.hooks import after_corporate_actions_written

        hvie_ca = after_corporate_actions_written(actions)
    except Exception as exc:
        hvie_ca = {"ok": False, "error": str(exc)[:200]}
    return _ok(
        "lidi_events",
        timeline=gateway.write("research_timeline", timeline, source="lidi", actor=actor,
                              reason="refresh:lidi_events"),
        corporate_actions=ca_result,
        hvie_ca=hvie_ca,
    )


def _action_kind(headline: str) -> Optional[str]:
    text = (headline or "").lower()
    for token, kind in (
        ("dividend", "dividend"),
        ("split", "split"),
        ("bonus", "bonus"),
        ("rights", "rights"),
        ("buyback", "buyback"),
        ("buy back", "buyback"),
        ("amalgamation", "merger"),
        ("merger", "merger"),
        ("demerger", "demerger"),
        ("name change", "name_change"),
        ("change in name", "name_change"),
        ("symbol change", "symbol_change"),
    ):
        if token in text:
            return kind
    return None


# --------------------------------------------------------------------------
# Stage: CGL (structured knowledge extracts)
# --------------------------------------------------------------------------


def stage_cgl(*, actor: str, limit: Optional[int] = None) -> dict[str, Any]:
    try:
        from continuous_gather_learn.persist import store_root
    except Exception as exc:
        return _fail("cgl", f"cgl_unavailable:{exc}")

    directory = store_root() / "knowledge"
    if not directory.exists():
        return _skip("cgl", "no_cgl_extracts")

    intelligence: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    for index, path in enumerate(sorted(directory.glob("*.json"))):
        if limit and index >= limit:
            break
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        symbol = str(payload.get("entity") or path.stem).strip().upper()
        if not symbol:
            continue
        themes = payload.get("themes") or []
        risks = payload.get("risks") or []
        catalysts = payload.get("catalysts") or []
        metrics = payload.get("metrics") or {}
        summary_bits = []
        if metrics.get("annual_periods"):
            summary_bits.append(f"{metrics['annual_periods']} annual periods of history")
        if metrics.get("revenue_cagr") is not None:
            summary_bits.append(f"revenue CAGR {metrics['revenue_cagr']}%")
        if metrics.get("earnings_cagr") is not None:
            summary_bits.append(f"earnings CAGR {metrics['earnings_cagr']}%")
        if metrics.get("max_drawdown") is not None:
            summary_bits.append(f"max drawdown {round(float(metrics['max_drawdown']) * 100, 1)}%")
        intelligence.append(
            {
                "symbol": symbol,
                "business_summary": "; ".join(summary_bits) or None,
                "key_risks": "; ".join(str(r) for r in risks) or None,
                "catalysts": "; ".join(str(c) for c in catalysts) or None,
                "source": "continuous_gather_learn",
            }
        )
        updated = to_date(payload.get("updated_at"))
        for theme in themes[:12]:
            if not updated:
                break
            timeline.append(
                {
                    "symbol": symbol,
                    "date": updated,
                    "event": str(theme),
                    "source": "continuous_gather_learn",
                }
            )
    return _ok(
        "cgl",
        company_intelligence=gateway.write("company_intelligence", intelligence,
                                          source="continuous_gather_learn", actor=actor,
                                          reason="refresh:cgl"),
        research_timeline=gateway.write("research_timeline", timeline,
                                       source="continuous_gather_learn", actor=actor,
                                       reason="refresh:cgl"),
    )


# --------------------------------------------------------------------------
# Stage: Knowledge Factory historical depth
# --------------------------------------------------------------------------


def _hd_records(kind: str, entity: str) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.historical_depth.store import get_series
    except Exception:
        return []
    payload = get_series(kind, entity) or {}
    records = payload.get("records")
    return records if isinstance(records, list) else []


def _hd_entities(kind: str) -> list[str]:
    try:
        from knowledge_factory.historical_depth.store import hd_root
    except Exception:
        return []
    directory = hd_root() / kind
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


def stage_knowledge_factory(*, actor: str, limit: Optional[int] = None) -> dict[str, Any]:
    prices: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    ownership: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    for entity in _hd_entities("prices")[: limit or None]:
        for record in _hd_records("prices", entity):
            payload = record.get("payload") or {}
            date = to_date(record.get("period_end")) or to_date(record.get("period"))
            close = to_number(payload.get("close"))
            if not date or close is None:
                continue
            prices.append(
                {
                    "symbol": entity.upper(),
                    "date": date,
                    "close": close,
                    "adjusted_close": to_number(payload.get("adj_close")),
                    "volume": to_number(payload.get("volume")),
                    "source": "knowledge_factory_hd",
                }
            )

    for entity in _hd_entities("corporate_actions")[: limit or None]:
        for record in _hd_records("corporate_actions", entity):
            payload = record.get("payload") or {}
            date = to_date(record.get("period_end")) or to_date(record.get("period"))
            kind = str(payload.get("action") or "").strip().lower()
            if not date or not kind:
                continue
            row = {
                "symbol": entity.upper(),
                "action_date": date,
                "action_type": kind,
                "details": json.dumps(payload, default=str),
                "source": "knowledge_factory_hd",
            }
            if kind == "dividend":
                row["dividend"] = to_number(payload.get("amount"))
            actions.append(row)

    for entity in _hd_entities("shareholding")[: limit or None]:
        for record in _hd_records("shareholding", entity):
            payload = record.get("payload") or {}
            date = to_date(record.get("period_end")) or to_date(record.get("period"))
            if not date:
                continue
            institutional = None
            fii, dii = to_number(payload.get("fii")), to_number(payload.get("dii"))
            if fii is not None or dii is not None:
                institutional = (fii or 0.0) + (dii or 0.0)
            ownership.append(
                {
                    "symbol": entity.upper(),
                    "as_of": date,
                    "promoter_holding": to_number(payload.get("promoter")),
                    "institutional_holding": institutional,
                    "fii": fii,
                    "dii": dii,
                    "mutual_funds": to_number(payload.get("mutual_funds")),
                    "public_holding": to_number(payload.get("public")),
                    "source": "knowledge_factory_hd",
                }
            )

    for entity in _hd_entities("timeline")[: limit or None]:
        for record in _hd_records("timeline", entity):
            payload = record.get("payload") or {}
            date = to_date(record.get("date")) or to_date(record.get("period_end"))
            title = str(payload.get("title") or record.get("title") or "").strip()
            if not date or not title:
                continue
            timeline.append(
                {
                    "symbol": entity.upper(),
                    "date": date,
                    "event": title,
                    "management": str(payload.get("type") or record.get("type") or "") or None,
                    "source": "knowledge_factory_hd",
                }
            )

    ca_result = gateway.write(
        "corporate_actions", actions, source="knowledge_factory_hd", actor=actor, reason="refresh:kf",
    )
    hvie_ca = None
    try:
        from historical_valuation_intelligence.hooks import after_corporate_actions_written

        hvie_ca = after_corporate_actions_written(actions)
    except Exception as exc:
        hvie_ca = {"ok": False, "error": str(exc)[:200]}
    return _ok(
        "knowledge_factory",
        daily_market_history=gateway.write("daily_market_history", prices, source="knowledge_factory_hd",
                                          actor=actor, reason="refresh:kf"),
        corporate_actions=ca_result,
        ownership=gateway.write("ownership", ownership, source="knowledge_factory_hd", actor=actor,
                               reason="refresh:kf"),
        research_timeline=gateway.write("research_timeline", timeline, source="knowledge_factory_hd",
                                       actor=actor, reason="refresh:kf"),
        hvie_ca=hvie_ca,
    )


# --------------------------------------------------------------------------
# Stage: financial statements (KF statements + FSE warehouse)
# --------------------------------------------------------------------------


def _statement_row(entity: str, record: dict[str, Any], *, annual: bool) -> Optional[dict[str, Any]]:
    payload = record.get("payload") or {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    period = str(record.get("period") or "").strip()
    if not period:
        return None
    row: dict[str, Any] = {
        "symbol": entity.upper(),
        "revenue": to_number(payload.get("revenue")),
        "ebitda": to_number(payload.get("ebitda")),
        "ebit": to_number(payload.get("ebit")),
        "pat": to_number(payload.get("net_income")),
        "eps": to_number(payload.get("eps")),
        "equity": to_number(payload.get("equity")),
        "debt": to_number(payload.get("total_debt")),
        "cash": to_number(payload.get("cash")),
        "cfo": to_number(payload.get("ocf")),
        "free_cash_flow": to_number(payload.get("fcf")),
        "source": str(record.get("source") or "knowledge_factory_hd"),
        "statement_version": str(payload.get("statement") or "mixed"),
    }
    units_in = payload.get("units_in") or metadata.get("units_in")
    if units_in:
        row["units_in"] = units_in
    source_document = payload.get("source_document") or metadata.get("xbrl_url")
    if source_document:
        row["source_document"] = source_document
    provider = payload.get("provider") or metadata.get("provider")
    parser_path = payload.get("parser_path") or metadata.get("parser_path")
    if provider and parser_path:
        row["statement_version"] = f"{provider}:{parser_path}"
    elif provider or parser_path:
        row["statement_version"] = str(provider or parser_path)
    if annual:
        row["fiscal_year"] = period
    else:
        row["fiscal_period"] = period
        row["fiscal_year"] = _fiscal_year_of(period)
        row["quarter"] = _quarter_of(period)
    if all(row.get(k) is None for k in ("revenue", "ebitda", "pat", "eps", "equity")):
        return None
    return row


def _fiscal_year_of(period: str) -> Optional[str]:
    match = re.search(r"(FY\s?\d{2,4})", period or "", re.IGNORECASE)
    return match.group(1).replace(" ", "").upper() if match else None


def _quarter_of(period: str) -> Optional[str]:
    match = re.search(r"(Q[1-4])", period or "", re.IGNORECASE)
    return match.group(1).upper() if match else None


def stage_financial_statements(*, actor: str, limit: Optional[int] = None) -> dict[str, Any]:
    annual_rows: list[dict[str, Any]] = []
    quarterly_rows: list[dict[str, Any]] = []

    for entity in _hd_entities("financials_annual")[: limit or None]:
        for record in _hd_records("financials_annual", entity):
            row = _statement_row(entity, record, annual=True)
            if row:
                annual_rows.append(row)
    for entity in _hd_entities("financials_quarterly")[: limit or None]:
        for record in _hd_records("financials_quarterly", entity):
            row = _statement_row(entity, record, annual=False)
            if row:
                quarterly_rows.append(row)

    warehouse_rows = _fse_rows(limit=limit)

    annual_all = annual_rows + warehouse_rows.get("annual", [])
    quarterly_all = quarterly_rows + warehouse_rows.get("quarterly", [])
    annual_result = gateway.write(
        "financials_annual", annual_all, source="knowledge_factory_hd", actor=actor,
        reason="refresh:statements",
    )
    quarterly_result = gateway.write(
        "financials_quarterly", quarterly_all, source="knowledge_factory_hd", actor=actor,
        reason="refresh:statements",
    )
    hvie_forward = None
    try:
        from historical_valuation_intelligence.hooks import after_statements_written

        hvie_forward = after_statements_written(annual_all + quarterly_all)
    except Exception as exc:
        hvie_forward = {"ok": False, "error": str(exc)[:200]}

    return _ok(
        "financial_statements",
        financials_annual=annual_result,
        financials_quarterly=quarterly_result,
        fse_rows=sum(len(v) for v in warehouse_rows.values()),
        hvie_forward=hvie_forward,
    )


def _fse_rows(*, limit: Optional[int] = None) -> dict[str, list[dict[str, Any]]]:
    """Pull parsed facts from the Financial Statements Engine warehouse when present."""
    out: dict[str, list[dict[str, Any]]] = {"annual": [], "quarterly": []}
    try:
        from financial_statements_engine.financial_warehouse import get_latest  # type: ignore
    except Exception:
        return out
    try:
        symbols = store.entities("company_master")[: limit or 200]
    except Exception:
        return out
    for symbol in symbols:
        try:
            facts = get_latest(symbol) or {}
        except Exception:
            continue
        periods = facts.get("periods") if isinstance(facts, dict) else None
        if not isinstance(periods, list):
            continue
        for period in periods:
            label = str(period.get("period") or period.get("fiscal_period") or "").strip()
            if not label:
                continue
            row = {
                "symbol": symbol,
                "revenue": to_number(period.get("revenue")),
                "ebitda": to_number(period.get("ebitda")),
                "pat": to_number(period.get("net_income") or period.get("pat")),
                "source": "fse_warehouse",
                "statement_version": "fse",
            }
            if str(period.get("frequency") or "").lower().startswith("q"):
                row["fiscal_period"] = label
                out["quarterly"].append(row)
            else:
                row["fiscal_year"] = label
                out["annual"].append(row)
    return out


# --------------------------------------------------------------------------
# Stage: research intelligence corpus
# --------------------------------------------------------------------------


def stage_research(*, actor: str) -> dict[str, Any]:
    try:
        from research_intelligence.corpus import get_corpus, list_entities
    except Exception as exc:
        return _skip("research", f"research_corpus_unavailable:{exc}")

    rows: list[dict[str, Any]] = []
    for entity in list_entities() or []:
        corpus = get_corpus(entity) or {}
        documents = corpus.get("documents") or corpus.get("cards") or []
        if isinstance(documents, dict):
            documents = list(documents.values())
        for document in documents:
            if not isinstance(document, dict):
                continue
            doc_type = str(document.get("doc_type") or document.get("type") or "note").strip()
            period = str(document.get("period") or document.get("fiscal_period") or "").strip()
            if not period:
                continue
            rows.append(
                {
                    "symbol": str(entity).upper(),
                    "document_type": doc_type,
                    "fiscal_period": period,
                    "management_themes": _join(document.get("themes")),
                    "strategy": _join(document.get("strategy")),
                    "risks": _join(document.get("risks")),
                    "opportunities": _join(document.get("opportunities")),
                    "capital_allocation": _join(document.get("capital_allocation")),
                    "guidance": _join(document.get("guidance")),
                    "events": _join(document.get("events")),
                    "summary": _join(document.get("summary")),
                    "confidence": to_number(document.get("confidence")),
                    "source": "research_intelligence",
                }
            )
    if not rows:
        return _skip("research", "no_research_documents")
    return _ok("research", research_intelligence=gateway.write(
        "research_intelligence", rows, source="research_intelligence", actor=actor,
        reason="refresh:research"))


def _join(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return "; ".join(parts) or None
    text = str(value).strip()
    return text or None


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

PIPELINE: tuple[str, ...] = (
    "groww",
    "yahoo",
    "capital_iq",
    "nse",
    "cgl",
    "knowledge_factory",
    "financial_statements",
    "research",
    "lidi_events",
    "validation",
    "recalculate",
    "publish",
    "hedge_fund_lab",
)


def stage_hedge_fund_lab(*, actor: str) -> dict[str, Any]:
    """Refresh Hedge Fund Strategy Lab snapshots from warehouse-backed scanners.

    Soft stage: an empty universe or import error must not fail the warehouse run.
    """
    try:
        from hedge_fund_lab.terminal import record_daily_snapshot
    except Exception as exc:
        return _skip("hedge_fund_lab", f"terminal_unavailable:{exc}")
    try:
        out = record_daily_snapshot(limit=1000)
    except Exception as exc:
        return _skip("hedge_fund_lab", f"snapshot_failed:{exc}")
    if not out.get("ok"):
        return _skip("hedge_fund_lab", str(out.get("error") or "universe_empty"), detail=out)
    return _ok("hedge_fund_lab", actor=actor, **{k: v for k, v in out.items() if k != "ok"})


def run(
    *,
    actor: str = "scheduler",
    stages: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
    days: int = 30,
) -> dict[str, Any]:
    wanted = [s for s in (stages or PIPELINE) if s in PIPELINE]
    run_id = uuid.uuid4().hex
    started = now_iso()
    db.execute(
        "INSERT INTO wh_refresh_runs (id, started_at, ok, actor, stages, counts, errors)"
        " VALUES (?, ?, 0, ?, ?, ?, ?)",
        (run_id, started, actor, json.dumps(wanted), "{}", "[]"),
    )

    runners: dict[str, Callable[[], dict[str, Any]]] = {
        "groww": lambda: stage_groww(actor=actor),
        "yahoo": lambda: stage_yahoo(actor=actor, limit=limit),
        "capital_iq": lambda: stage_capital_iq(actor=actor, limit=limit),
        "nse": lambda: stage_nse(actor=actor, days=days),
        "cgl": lambda: stage_cgl(actor=actor, limit=limit),
        "knowledge_factory": lambda: stage_knowledge_factory(actor=actor, limit=limit),
        "financial_statements": lambda: stage_financial_statements(actor=actor, limit=limit),
        "research": lambda: stage_research(actor=actor),
        "lidi_events": lambda: stage_lidi_events(actor=actor),
        # Validation reports on data, it does not fail the run: a tab with dirty
        # rows is a finding to act on, not a broken pipeline.
        "validation": lambda: {"stage": "validation", "ok": True,
                               "report": validation.validate_all(sample=200)},
        "recalculate": lambda: {"stage": "recalculate", **recalculate(actor=actor)},
        "publish": lambda: _publish_all(actor=actor),
        "hedge_fund_lab": lambda: stage_hedge_fund_lab(actor=actor),
    }

    results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    for stage in wanted:
        try:
            results[stage] = runners[stage]()
            if results[stage].get("ok") is False:
                errors.append({"stage": stage, "error": str(results[stage].get("error") or "stage_failed")})
        except Exception as exc:
            results[stage] = _fail(stage, str(exc))
            errors.append({"stage": stage, "error": str(exc)})

    counts = {tab: store.row_count(tab) for tab in [t for t in _tab_ids()]}
    finished = now_iso()
    db.execute(
        "UPDATE wh_refresh_runs SET finished_at = ?, ok = ?, counts = ?, errors = ? WHERE id = ?",
        (finished, 0 if errors else 1, json.dumps(counts), json.dumps(errors), run_id),
    )
    audit.record("refresh", actor=actor, detail={"run_id": run_id, "stages": wanted, "errors": errors},
                 ok=not errors)
    return {
        "ok": not errors,
        "run_id": run_id,
        "started_at": started,
        "finished_at": finished,
        "stages": results,
        "errors": errors,
        "row_counts": counts,
    }


def _tab_ids() -> list[str]:
    from institutional_warehouse.schema import tab_ids

    return tab_ids()


def _publish_all(*, actor: str) -> dict[str, Any]:
    published = {}
    for tab_id in _tab_ids():
        published[tab_id] = store.publish(tab_id, actor=actor).get("published", 0)
    return {"stage": "publish", "ok": True, "published": published}


def recent_runs(limit: int = 20) -> dict[str, Any]:
    rows = db.query(
        "SELECT id, started_at, finished_at, ok, actor, stages, counts, errors FROM wh_refresh_runs"
        " ORDER BY started_at DESC LIMIT ?",
        (max(1, min(int(limit), 200)),),
    )
    out = []
    for row in rows:
        out.append(
            {
                "id": row.get("id"),
                "started_at": row.get("started_at"),
                "finished_at": row.get("finished_at"),
                "ok": bool(row.get("ok")),
                "actor": row.get("actor"),
                "stages": _loads(row.get("stages"), []),
                "counts": _loads(row.get("counts"), {}),
                "errors": _loads(row.get("errors"), []),
            }
        )
    return {"ok": True, "runs": out}


def _loads(raw: Any, fallback: Any) -> Any:
    try:
        return json.loads(raw) if raw else fallback
    except Exception:
        return fallback
