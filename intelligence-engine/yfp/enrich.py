"""Soft-merge Yahoo canonical enrichment into CID — never overwrite higher-confidence fields."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def merge_yahoo_into_dossier(dossier: dict[str, Any], enrich: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich CID from MarketDataClient.yahoo_enrich() canonical package.
    Yahoo is secondary: only fill empty / missing fields.
    """
    if not isinstance(dossier, dict) or not isinstance(enrich, dict) or not enrich.get("enabled"):
        return dossier
    now = datetime.now(timezone.utc).isoformat()
    d = dict(dossier)

    quote = enrich.get("quote") if isinstance(enrich.get("quote"), dict) else {}
    fund = enrich.get("fundamentals") if isinstance(enrich.get("fundamentals"), dict) else {}
    metrics = fund.get("metrics") if isinstance(fund.get("metrics"), dict) else {}

    # Identity / business profile
    ident = dict(d.get("identity") or {})
    _fill(ident, "company_name", metrics.get("company_name"))
    _fill(ident, "sector", metrics.get("sector"))
    _fill(ident, "industry", metrics.get("industry"))
    _fill(ident, "market_cap", metrics.get("market_cap") or quote.get("market_cap"))
    d["identity"] = ident

    biz = dict(d.get("business_profile") or {})
    _fill(biz, "business_model", metrics.get("business_summary"))
    if metrics.get("business_summary") and not biz.get("products"):
        biz["products"] = []
    d["business_profile"] = biz

    mgmt = dict(d.get("management") or {})
    _fill(mgmt, "ceo", metrics.get("ceo"))
    _fill(mgmt, "cfo", metrics.get("cfo"))
    if metrics.get("officers_json") and not mgmt.get("board"):
        try:
            officers = json.loads(metrics["officers_json"])
            mgmt["board"] = officers if isinstance(officers, list) else []
        except Exception:
            pass
    d["management"] = mgmt

    # Market data — fill empties only
    md = dict(d.get("market_data") or {})
    _fill(md, "current_price", quote.get("last"))
    _fill(md, "volume", quote.get("volume") or metrics.get("volume"))
    _fill(md, "market_cap", metrics.get("market_cap"))
    _fill(md, "fifty_two_week_high", metrics.get("fifty_two_week_high"))
    _fill(md, "fifty_two_week_low", metrics.get("fifty_two_week_low"))
    _fill(md, "dividend_yield", metrics.get("dividend_yield"))
    _fill(md, "beta", metrics.get("beta") or metrics.get("beta_summary"))
    _fill(md, "enterprise_value", metrics.get("enterprise_value"))
    multiples = dict(md.get("valuation_multiples") or {})
    for k in ("trailing_pe", "forward_pe", "price_to_book", "price_to_sales", "ev_ebitda", "peg"):
        if metrics.get(k) is not None and multiples.get(k) is None:
            multiples[k] = metrics.get(k)
    if multiples:
        md["valuation_multiples"] = multiples
    if quote.get("last") is not None:
        hist = list(md.get("historical_prices") or [])
        hist.append({"at": now, "price": quote.get("last"), "source": "yahoo"})
        md["historical_prices"] = hist[-120:]
    md["updated_at"] = md.get("updated_at") or now
    d["market_data"] = md

    # Financial metrics
    fm = dict(d.get("financial_metrics") or {})
    for src, dest in (
        ("roe", "roe"),
        ("roa", "roa"),
        ("revenue_growth", "revenue_growth"),
        ("operating_margin", "operating_margin"),
        ("profit_margin", "net_margin"),
        ("gross_margin", "gross_margin"),
        ("free_cash_flow", "fcf"),
        ("current_ratio", "current_ratio"),
        ("ebitda", "ebitda"),
        ("revenue", "revenue"),
    ):
        if metrics.get(src) is not None and fm.get(dest) is None:
            fm[dest] = metrics.get(src)
    d["financial_metrics"] = fm

    # Valuation
    val = dict(d.get("valuation") or {})
    current = dict(val.get("current") or {})
    for k in ("trailing_pe", "forward_pe", "price_to_book", "enterprise_value", "market_cap", "target_mean_price"):
        if metrics.get(k) is not None and current.get(k) is None:
            current[k] = metrics.get(k)
    if current:
        val["current"] = current
        hist = list(val.get("historical") or [])
        hist.append({"at": now, "valuation": current, "source": "yahoo"})
        val["historical"] = hist[-40:]
    if metrics.get("recommendation_key") and not val.get("confidence"):
        val["confidence"] = metrics.get("recommendation_key")
    d["valuation"] = val

    # Financial statements versions from JSON metrics
    fs = dict(d.get("financial_statements") or {})
    for metric_key, period, stmt in (
        ("income_statement_annual_json", "annual", "income_statement"),
        ("income_statement_quarterly_json", "quarterly", "income_statement"),
        ("balance_sheet_annual_json", "annual", "balance_sheet"),
        ("balance_sheet_quarterly_json", "quarterly", "balance_sheet"),
        ("cashflow_annual_json", "annual", "cash_flow"),
        ("cashflow_quarterly_json", "quarterly", "cash_flow"),
    ):
        raw = metrics.get(metric_key)
        if not raw:
            continue
        try:
            rows = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        block = dict(fs.get(stmt) or {"annual": [], "quarterly": []})
        arr = list(block.get(period) or [])
        if rows and not arr:
            arr.append({"at": now, "source": "yahoo", "rows": rows[:4]})
            block[period] = arr
            fs[stmt] = block
            versions = list(fs.get("versions") or [])
            versions.append({"at": now, "source": "yahoo", "statement": stmt, "period": period})
            fs["versions"] = versions[-80:]
    d["financial_statements"] = fs

    # Ownership / peer-ish
    peer = dict(d.get("peer_comparison") or {})
    if metrics.get("institutions_percent") is not None:
        peer.setdefault("ownership", {})
        if isinstance(peer["ownership"], dict) and peer["ownership"].get("institutions_percent") is None:
            peer["ownership"]["institutions_percent"] = metrics.get("institutions_percent")
            peer["ownership"]["insiders_percent"] = metrics.get("insiders_percent")
    d["peer_comparison"] = peer

    # Announcements / timeline from calendar events (append-only)
    timeline = list(d.get("evidence_timeline") or [])
    seen = {e.get("evidence_id") for e in timeline if e.get("evidence_id")}
    for ev in enrich.get("calendar_events") or []:
        if not isinstance(ev, dict):
            continue
        eid = f"yahoo:{ev.get('event_id')}"
        if eid in seen:
            continue
        timeline.append(
            {
                "at": now,
                "evidence_id": eid,
                "evidence_type": ev.get("event_type") or "calendar_event",
                "category": "corporate_announcements",
                "title": ev.get("title"),
                "source_id": "yahoo",
                "confidence": 0.7,
                "verification_status": "provisionally_verified",
                "value_text": str(ev.get("details") or "")[:400],
                "url": (ev.get("details") or {}).get("url") if isinstance(ev.get("details"), dict) else None,
            }
        )
        seen.add(eid)
        if ev.get("event_type") in {"earnings", "earnings_history", "upgrade_downgrade", "sec_filing"}:
            anns = list(d.get("announcements") or [])
            anns.append(
                {
                    "evidence_id": eid,
                    "title": ev.get("title"),
                    "source_id": "yahoo",
                    "published": ev.get("event_time") or now,
                    "announcement_kind": ev.get("event_type"),
                }
            )
            d["announcements"] = anns[-120:]
            d["latest_announcement"] = anns[-1]
    d["evidence_timeline"] = timeline[-500:]

    # Corporate actions → announcements
    for act in enrich.get("corporate_actions") or []:
        if not isinstance(act, dict):
            continue
        eid = f"yahoo:ca:{act.get('action_type')}:{act.get('ex_date')}"
        if eid in seen:
            continue
        timeline_item = {
            "at": now,
            "evidence_id": eid,
            "evidence_type": "corporate_announcement",
            "category": "corporate_announcements",
            "title": f"{act.get('action_type')} {act.get('ex_date')}",
            "source_id": "yahoo",
            "confidence": 0.75,
            "verification_status": "provisionally_verified",
            "value_text": str(act.get("details") or act)[:400],
        }
        d.setdefault("evidence_timeline", []).append(timeline_item)

    # Canonical financial / valuation history (YAHOO_FINANCIAL_HISTORY / VALUATION_HISTORY)
    d = merge_financial_intelligence(d, enrich, now=now)

    # Provenance stamp
    d.setdefault("enrichment", {})
    d["enrichment"]["yahoo"] = {
        "provider_id": "yahoo",
        "role": "secondary",
        "enriched_at": now,
        "has_quote": bool(quote),
        "has_fundamentals": bool(metrics),
        "calendar_events": len(enrich.get("calendar_events") or []),
        "has_financial_history": bool(enrich.get("financial_history")),
        "has_valuation_snapshot": bool((enrich.get("valuation_snapshot") or {}).get("metrics")),
    }
    d["updated_at"] = now
    return d


def merge_financial_intelligence(
    dossier: dict[str, Any],
    enrich: dict[str, Any],
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Fill CID financial history / valuation timeline / KPI trends from canonical YFP pack."""
    from yfp.history import (
        dvc_fields_from_valuation,
        financial_coverage,
        kpi_trends,
        valuation_coverage,
    )

    now = now or datetime.now(timezone.utc).isoformat()
    d = dict(dossier)
    fh = enrich.get("financial_history") if isinstance(enrich.get("financial_history"), dict) else {}
    vs = enrich.get("valuation_snapshot") if isinstance(enrich.get("valuation_snapshot"), dict) else {}

    if fh and (fh.get("income_statement") or fh.get("balance_sheet") or fh.get("cash_flow")):
        fs = dict(d.get("financial_statements") or {})
        for stmt in ("income_statement", "balance_sheet", "cash_flow"):
            block = dict(fs.get(stmt) or {"annual": [], "quarterly": []})
            for period in ("annual", "quarterly"):
                new_rows = list((fh.get(stmt) or {}).get(period) or [])
                if not new_rows:
                    continue
                arr = list(block.get(period) or [])
                # Fill empties only — if institutional rows already present, skip overwrite
                if not arr:
                    block[period] = [
                        {
                            "at": now,
                            "source": "yahoo",
                            "provider_id": "yahoo",
                            "provider_priority": 40,
                            "period_rows": new_rows,
                            "row_count": len(new_rows),
                        }
                    ]
                    versions = list(fs.get("versions") or [])
                    versions.append(
                        {
                            "at": now,
                            "source": "yahoo",
                            "statement": stmt,
                            "period": period,
                            "row_count": len(new_rows),
                        }
                    )
                    fs["versions"] = versions[-80:]
                else:
                    # Append timeline version if newer periods available and not duplicate
                    existing_ends = set()
                    for entry in arr:
                        for pr in entry.get("period_rows") or entry.get("rows") or []:
                            if isinstance(pr, dict) and pr.get("period_end"):
                                existing_ends.add(str(pr.get("period_end")))
                    novel = [r for r in new_rows if str(r.get("period_end")) not in existing_ends]
                    if novel and not any(e.get("source") == "yahoo" for e in arr):
                        arr.append(
                            {
                                "at": now,
                                "source": "yahoo",
                                "provider_id": "yahoo",
                                "period_rows": novel,
                                "row_count": len(novel),
                            }
                        )
                        block[period] = arr[-6:]
            fs[stmt] = block
        # Legacy JSON metric fallback still handled above in merge_yahoo_into_dossier
        fs["coverage"] = financial_coverage(fh)
        d["financial_statements"] = fs
        d["financial_history"] = {
            "provider_id": "yahoo",
            "counts": fh.get("counts"),
            "currency": fh.get("currency"),
            "kpi_trends": kpi_trends(fh),
            "coverage": financial_coverage(fh),
            "updated_at": now,
        }
        # Historical KPI trends side-car
        d["historical_kpi_trends"] = kpi_trends(fh)

        # Evidence timeline — financial history markers (append-only)
        timeline = list(d.get("evidence_timeline") or [])
        seen = {e.get("evidence_id") for e in timeline if e.get("evidence_id")}
        key_map = {
            "income_statement": "income_annual",
            "balance_sheet": "balance_annual",
            "cash_flow": "cashflow_annual",
        }
        for stmt, label in (
            ("income_statement", "Income statement history"),
            ("balance_sheet", "Balance sheet history"),
            ("cash_flow", "Cash flow history"),
        ):
            n = int((fh.get("counts") or {}).get(key_map[stmt]) or 0)
            if n <= 0:
                continue
            eid = f"yfp:fs:{stmt}:{d.get('ticker')}"
            if eid in seen:
                continue
            timeline.append(
                {
                    "at": now,
                    "evidence_id": eid,
                    "evidence_type": "financial_statements",
                    "category": "financial_statements",
                    "title": f"{label} ({n} annual periods)",
                    "source_id": "yahoo",
                    "confidence": 0.74,
                    "verification_status": "provisionally_verified",
                    "value_text": f"{n} annual periods ingested (canonical)",
                }
            )
            seen.add(eid)
        d["evidence_timeline"] = timeline[-500:]

    if vs and (vs.get("metrics") or {}):
        metrics = vs.get("metrics") or {}
        val = dict(d.get("valuation") or {})
        current = dict(val.get("current") or {})
        for k, v in metrics.items():
            if v is not None and current.get(k) is None:
                current[k] = v
        if current:
            val["current"] = current
            hist = list(val.get("historical") or [])
            hist.append(
                {
                    "at": now,
                    "as_of": vs.get("as_of") or now,
                    "valuation": metrics,
                    "source": "yahoo",
                    "provider_id": "yahoo",
                    "provider_priority": 40,
                }
            )
            val["historical"] = hist[-60:]
            val["timeline"] = list(val.get("timeline") or [])
            val["timeline"].append({"at": now, "metrics": metrics, "source": "yahoo"})
            val["timeline"] = val["timeline"][-80:]
            val["coverage"] = valuation_coverage(vs)
        d["valuation"] = val

        # Market data multiples fill empties
        md = dict(d.get("market_data") or {})
        _fill(md, "market_cap", metrics.get("market_cap"))
        _fill(md, "enterprise_value", metrics.get("enterprise_value"))
        _fill(md, "dividend_yield", metrics.get("dividend_yield"))
        _fill(md, "beta", metrics.get("beta"))
        multiples = dict(md.get("valuation_multiples") or {})
        for k in ("trailing_pe", "forward_pe", "price_to_book", "price_to_sales", "ev_ebitda", "peg"):
            if metrics.get(k) is not None and multiples.get(k) is None:
                multiples[k] = metrics.get(k)
        if multiples:
            md["valuation_multiples"] = multiples
        d["market_data"] = md

        # Soft DVC validated_fields for valuation (fill empties only)
        existing_vf = dict(d.get("validated_fields") or {})
        for field, vf in dvc_fields_from_valuation(vs).items():
            if field not in existing_vf or existing_vf.get(field, {}).get("value") in (None, ""):
                existing_vf[field] = vf
        d["validated_fields"] = existing_vf

        # Financial coverage panel for admin
        d["financial_coverage"] = {
            "financial": financial_coverage(fh) if fh else {},
            "valuation": valuation_coverage(vs),
            "updated_at": now,
            "provider_id": "yahoo",
        }

    return d


def _fill(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None or value == "":
        return
    if target.get(key) in (None, "", [], {}):
        target[key] = value


def fundamentals_to_kip_facts(enrich: dict[str, Any]) -> list[dict[str, Any]]:
    """Structured facts for KIP soft ingest — never raw Yahoo payloads."""
    facts: list[dict[str, Any]] = []
    fund = enrich.get("fundamentals") if isinstance(enrich.get("fundamentals"), dict) else {}
    metrics = fund.get("metrics") if isinstance(fund.get("metrics"), dict) else {}
    symbol = enrich.get("symbol") or fund.get("symbol")
    for key in (
        "sector",
        "industry",
        "roe",
        "roa",
        "trailing_pe",
        "forward_pe",
        "market_cap",
        "enterprise_value",
        "revenue_growth",
        "operating_margin",
        "dividend_yield",
        "beta",
    ):
        if metrics.get(key) is not None:
            facts.append(
                {
                    "fact_key": key,
                    "value": metrics.get(key),
                    "symbol": symbol,
                    "source_id": "yahoo",
                    "confidence": 0.68,
                }
            )
    return facts
