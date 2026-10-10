"""Institutional Valuation Terminal — Warehouse → Engine → Screen.

Replaces the Yahoo JSON snapshot path. Every number the terminal shows is
computed by the Unified Valuation Engine from warehouse rows, with coverage,
provenance and a health score attached so an analyst can trust (or discount)
the view.
"""

from __future__ import annotations

from statistics import median
from datetime import datetime, timezone
from math import log10
from typing import Any, Optional

from valuation_engine import attribution, engine, health_score, service
from valuation_engine.service import ENGINE_CODE, VERSION, _as_number, _percentile, _visible

#: Multiples shown in the institutional table.
TABLE_METRICS = ("pe", "pb", "ev_ebitda", "ev_sales", "ps", "roe", "dividend_yield", "forward_pe")

#: Charts the terminal offers, coverage-aware via the history API.
CHART_METRICS = ("price", "pe", "pb", "ev_ebitda", "revenue", "eps", "roe", "dividend_yield")

WINDOWS = ("1Y", "3Y", "5Y", "10Y", "MAX")

#: Higher-is-better metrics (position language flips for these).
_HIGHER_BETTER = frozenset({"roe", "dividend_yield"})


def health() -> dict[str, Any]:
    """Terminal health: engine contract + warehouse coverage, not JSON rows."""
    from institutional_warehouse.production import coverage as wh_coverage

    base = service.health()
    warehouse = wh_coverage()
    return {
        **base,
        "page": "Institutional Valuation Terminal",
        "data_path": "warehouse → unified_valuation_engine → terminal",
        "json_loader": "retired",
        "companies": warehouse.get("companies"),
        "warehouse_rows": warehouse.get("total_rows"),
        "updated_at": None,
    }


def search(query: str, *, limit: int = 12) -> dict[str, Any]:
    """Institutional company search over company_master."""
    from institutional_warehouse.production import suggest

    result = suggest(query, limit=limit)
    suggestions = result.get("suggestions") or []
    return {
        "ok": True,
        "query": query,
        "suggestions": [
            {
                "symbol": s.get("symbol"),
                "name": s.get("name") or s.get("company_name") or s.get("symbol"),
            }
            for s in suggestions
        ],
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def company_pack(symbol: str, *, window: str = "5Y", peer_limit: int = 12) -> dict[str, Any]:
    """Everything the terminal needs for one company, in one response."""
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "empty_symbol", "engine": ENGINE_CODE, "version": VERSION}

    from institutional_warehouse.production import read_company

    record = read_company(ticker)
    if not record or not record.get("ok", True):
        return {
            "ok": False,
            "symbol": ticker,
            "error": "not_in_warehouse",
            "engine": ENGINE_CODE,
            "version": VERSION,
        }

    peers_raw, peer_valuations = _load_peers(record, limit=peer_limit)
    history_rows = _load_history_rows(ticker)
    valuation = service.get_company_valuation(
        ticker, record=record, peers=peer_valuations, history=history_rows,
    )

    metrics = valuation.get("metrics") or {}
    context = valuation.get("context") or {}
    policy = valuation.get("policy") or {}
    master = record.get("master") or {}
    industry_dna = (
        (valuation.get("company") or {}).get("industry")
        or master.get("industry_dna")
        or master.get("industry")
    )

    table = _institutional_table(metrics, context, industry_dna, policy)
    sector_context = _sector_context(valuation, peer_valuations)
    peers = _peer_table(ticker, metrics, peer_valuations, context)
    explanation = _explanation(ticker, valuation, sector_context)
    change = _change_log(ticker, metrics, history_rows)
    charts = _chart_coverage(ticker, window)
    dq = _data_quality(ticker, record)
    provenance = {**(valuation.get("provenance") or {}), "freshness": dq.get("freshness") or {}}
    hist_span, hist_obs = _history_depth(history_rows, charts)
    confidence = health_score.score(
        metrics=metrics,
        coverage=valuation.get("coverage") or {},
        provenance=provenance,
        history_span_years=hist_span,
        history_observations=hist_obs,
        conflict_count=int(dq.get("conflicts") or 0),
        override_count=int(dq.get("overrides") or 0),
        quality_flags={"dqiv_passed": dq.get("validated")},
    )

    overview = _overview(record, metrics, valuation, charts, confidence)

    return {
        "ok": True,
        "symbol": ticker,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "window": window.upper(),
        "overview": overview,
        "table": table,
        "sector_context": sector_context,
        "peers": peers,
        "explanation": explanation,
        "change_log": change,
        "charts": charts,
        "coverage": valuation.get("coverage"),
        "provenance": provenance,
        "data_quality": dq,
        "health_score": confidence,
        "lens": valuation.get("lens"),
        "policy": policy,
        "metrics": metrics,
        "context": context,
        "company": valuation.get("company"),
    }


def chart_series(symbol: str, metric: str, *, window: str = "5Y") -> dict[str, Any]:
    """One coverage-aware chart series for the terminal."""
    from institutional_warehouse.production import history_series

    win = _norm_window(window)
    series = history_series(symbol, metric, window=win)
    if not series.get("ok"):
        return {**series, "engine": ENGINE_CODE, "version": VERSION}
    stats = series.get("stats") or {}
    return {
        "ok": True,
        "symbol": str(symbol or "").upper(),
        "metric": metric,
        "window": win,
        "points": series.get("points") or [],
        "count": series.get("count") or 0,
        "first": series.get("first"),
        "last": series.get("last"),
        "coverage": {
            "history": series.get("count") or 0,
            "confidence": _series_confidence(series.get("count") or 0, stats.get("years")),
            "observed_span": stats.get("years"),
            "first": series.get("first"),
            "last": series.get("last"),
            "current_percentile": stats.get("current_percentile"),
            "median": stats.get("median"),
        },
        "stats": stats,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def explain_metric(metric: str) -> dict[str, Any]:
    """Keep the existing pedagogy; the terminal still teaches the metric."""
    try:
        from valuation_terminal.sector_lens import explain

        body = explain(metric) or {}
        return {"ok": True, "metric": metric, **body}
    except Exception as exc:
        return {"ok": False, "metric": metric, "error": str(exc)[:160]}


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _norm_window(window: str) -> str:
    raw = str(window or "5Y").strip().lower().replace("y", "y")
    mapping = {"1y": "1y", "3y": "3y", "5y": "5y", "10y": "10y", "max": "max"}
    return mapping.get(raw.replace(" ", ""), "5y")


def _load_history_rows(symbol: str, limit: int = 400) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    try:
        rows = store.all_rows("historical_valuation", entity=symbol, limit=limit)
    except Exception:
        return []
    rows = sorted(rows, key=lambda r: str(r.get("date") or ""))
    return rows


def _peer_rank(target: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, str]:
    """Rank peers by business similarity before a stable symbol tie-breaker."""
    target_dna = str(target.get("industry_dna") or target.get("industry") or "").strip().lower()
    candidate_dna = str(candidate.get("industry_dna") or candidate.get("industry") or "").strip().lower()
    score = 0.0
    reason = "same sector"
    if target_dna and target_dna == candidate_dna:
        score += 100.0
        reason = "same industry"
    target_cap = _as_number(target.get("market_cap"))
    candidate_cap = _as_number(candidate.get("market_cap"))
    if target_cap and candidate_cap and target_cap > 0 and candidate_cap > 0:
        # Penalise size distance, but industry similarity remains dominant.
        score -= min(30.0, abs(log10(target_cap) - log10(candidate_cap)) * 10.0)
        reason += ", similar size"
    return score, reason


def _load_peers(record: dict[str, Any], *, limit: int = 12) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Comparable equities, ranked by industry and size—not alphabetically."""
    from institutional_warehouse import store
    from institutional_warehouse.production import read_company
    from valuation_policy.instruments import resolve_instrument

    master = record.get("master") or {}
    sector = master.get("sector")
    symbol = str(record.get("symbol") or "").upper()
    if not sector:
        return [], []

    try:
        candidates = [
            r for r in store.all_rows("company_master", limit=4000)
            if str(r.get("sector") or "") == sector
            and str(r.get("symbol") or "").upper() != symbol
        ]
    except Exception:
        return [], []

    ranked = []
    for candidate in candidates:
        kind = resolve_instrument(
            symbol=str(candidate.get("symbol") or ""), company_name=candidate.get("company_name"),
            sector=candidate.get("sector"), industry=candidate.get("industry"),
            industry_dna=candidate.get("industry_dna"), master=candidate,
        ).get("instrument_type")
        if kind != "EQUITY":
            continue
        score, reason = _peer_rank(master, candidate)
        ranked.append((score, str(candidate.get("symbol") or ""), reason, candidate))
    # Assess a small, quality-ranked candidate pool; do not do a full-universe
    # expensive company read on every terminal request.
    ranked.sort(key=lambda x: (-x[0], x[1]))
    candidates = ranked[: max(24, limit * 4)]
    peer_rows: list[dict[str, Any]] = []
    peer_vals: list[dict[str, Any]] = []
    for _, _, peer_reason, row in candidates:
        ticker = str(row.get("symbol") or "").upper()
        if not ticker:
            continue
        try:
            peer_record = read_company(ticker)
            if not peer_record.get("ok", True):
                continue
            values = engine.compute(peer_record)
            # A peer without both a current value and an annual statement is
            # not a comparable company for valuation purposes.
            if not peer_record.get("latest_annual") or not any(v.available for v in values.values()):
                continue
            flat = {k: v.value for k, v in values.items() if v.available}
            flat["symbol"] = ticker
            flat["company_name"] = (peer_record.get("master") or {}).get("company_name") or ticker
            flat["sector"] = sector
            flat["peer_reason"] = peer_reason
            peer_rows.append(flat)
            # Shape expected by service.get_company_valuation peer_series.
            peer_vals.append(flat)
            if len(peer_vals) >= limit:
                break
        except Exception:
            continue
    return peer_rows, peer_vals


def _position(metric: str, company: Optional[float], reference: Optional[float]) -> Optional[str]:
    if company is None or reference is None or reference == 0:
        return None
    premium = (company - reference) / abs(reference)
    if metric in _HIGHER_BETTER:
        if premium >= 0.05:
            return "Above"
        if premium <= -0.05:
            return "Below"
        return "In line"
    if premium >= 0.05:
        return "Premium"
    if premium <= -0.05:
        return "Discount"
    return "In line"


def _institutional_table(
    metrics: dict[str, Any],
    context: dict[str, Any],
    industry_dna: Optional[str],
    policy: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    rows = []
    for name in TABLE_METRICS:
        if not _visible(name, industry_dna, policy):
            applicability = ((metrics.get(name) or {}).get("applicability") or {})
            rows.append({
                "metric": name,
                "meaningful": False,
                "company": None,
                "industry": None,
                "historical": None,
                "position": None,
                "source": None,
                "note": applicability.get("reason") or "not meaningful for this industry",
                "applicability": applicability or {
                    "status": "Hidden",
                    "reason": "Suppressed by valuation policy.",
                },
            })
            continue
        cell = metrics.get(name) or {}
        ctx = context.get(name) or {}
        company = cell.get("value")
        industry = ctx.get("sector_median")
        historical = ctx.get("historical_median")
        # Prefer industry for position; fall back to historical.
        position = _position(name, company, industry if industry is not None else historical)
        sources = cell.get("sources") or []
        rows.append({
            "metric": name,
            "meaningful": True,
            "company": company,
            "industry": industry,
            "historical": historical,
            "position": position,
            "source": sources[0] if sources else ("Engine" if cell.get("available") else None),
            "sources": sources,
            "available": bool(cell.get("available")),
            "missing": cell.get("missing") or [],
            "note": cell.get("note") or "",
            "applicability": cell.get("applicability"),
        "coverage": {
                "peer_count": ctx.get("peer_count"),
                "observations": ctx.get("observations"),
                "historical_percentile": ctx.get("historical_percentile"),
            "premium_pct": ctx.get("premium_pct"),
            "historical_observation_label": (
                f"{ctx.get('observations')} observations" if ctx.get("observations") else "No historical observations"
            ),
            },
        })
    return rows


def _sector_context(valuation: dict[str, Any], peer_vals: list[dict[str, Any]]) -> dict[str, Any]:
    company = valuation.get("company") or {}
    sector = company.get("sector")
    context = valuation.get("context") or {}
    policy = valuation.get("policy") or {}
    lens = valuation.get("lens") or {}
    # VPAE primary first; else first comparable with a sector median.
    primary = policy.get("primary_metric") or lens.get("primary_metric") or "pe"
    if (context.get(primary) or {}).get("sector_median") is None:
        for candidate in ("pe", "pb", "ev_ebitda", "roe", "ev_sales"):
            if (context.get(candidate) or {}).get("sector_median") is not None:
                primary = candidate
                break
    own = ((valuation.get("metrics") or {}).get(primary) or {}).get("value")
    series = [v for v in (_as_number(p.get(primary)) for p in peer_vals) if v is not None]
    if own is not None:
        series_with_own = sorted(series + [own])
    else:
        series_with_own = sorted(series)
    rank = None
    if own is not None and series_with_own:
        # Rank 1 = cheapest (lowest multiple) for valuation multiples.
        ordered = sorted(series_with_own)
        rank = ordered.index(own) + 1 if own in ordered else None
    return {
        "sector": sector,
        "primary_metric": primary,
        "current_median": (context.get(primary) or {}).get("sector_median"),
        "historical_median": (context.get(primary) or {}).get("historical_median"),
        "current_rank": rank,
        "universe": len(series_with_own),
        "distribution": {
            "low": series_with_own[0] if series_with_own else None,
            "high": series_with_own[-1] if series_with_own else None,
            "median": round(median(series_with_own), 4) if series_with_own else None,
            "count": len(series_with_own),
        },
        "peer_percentile": _percentile(own, series) if own is not None else None,
        "metrics": {
            name: {
                "current_median": (context.get(name) or {}).get("sector_median"),
                "historical_median": (context.get(name) or {}).get("historical_median"),
                "premium_pct": (context.get(name) or {}).get("premium_pct"),
                "peer_count": (context.get(name) or {}).get("peer_count"),
            }
            for name in TABLE_METRICS
        },
    }


def _relative_score(
    metrics: dict[str, Any],
    context: dict[str, Any],
) -> Optional[float]:
    """0–100: cheaper vs peers/history and stronger ROE score higher.

    Not investment advice — a relative positioning aid inside the peer set.
    """
    bits: list[float] = []
    for name in ("pe", "pb", "ev_ebitda"):
        ctx = context.get(name) or {}
        premium = ctx.get("premium_pct")
        hist = ctx.get("historical_percentile")
        if premium is not None:
            # Negative premium (discount) → higher score.
            bits.append(max(0.0, min(100.0, 50.0 - float(premium))))
        if hist is not None:
            bits.append(max(0.0, min(100.0, 100.0 - float(hist))))
    roe = (metrics.get("roe") or {}).get("value")
    if roe is not None:
        bits.append(max(0.0, min(100.0, float(roe) * 2.5)))
    if not bits:
        return None
    return round(sum(bits) / len(bits), 1)


def _peer_table(
    symbol: str,
    metrics: dict[str, Any],
    peer_vals: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    own_score = _relative_score(metrics, context)
    rows = [{
        "symbol": symbol,
        "company_name": "This company",
        "is_self": True,
        "pe": (metrics.get("pe") or {}).get("value"),
        "pb": (metrics.get("pb") or {}).get("value"),
        "ev_ebitda": (metrics.get("ev_ebitda") or {}).get("value"),
        "roe": (metrics.get("roe") or {}).get("value"),
        "historical_pe": (context.get("pe") or {}).get("historical_median"),
        "consensus_upside": (metrics.get("upside") or {}).get("value"),
        "relative_score": own_score,
    }]
    for peer in peer_vals:
        # Approximate peer context with own sector medians for relative score.
        peer_ctx = {
            name: {
                "premium_pct": (
                    round(100.0 * (peer[name] - (context.get(name) or {}).get("sector_median"))
                          / (context.get(name) or {}).get("sector_median"), 2)
                    if peer.get(name) is not None and (context.get(name) or {}).get("sector_median")
                    else None
                ),
                "historical_percentile": None,
            }
            for name in ("pe", "pb", "ev_ebitda")
        }
        peer_metrics = {k: {"value": peer.get(k)} for k in ("pe", "pb", "ev_ebitda", "roe")}
        rows.append({
            "symbol": peer.get("symbol"),
            "company_name": peer.get("company_name") or peer.get("symbol"),
            "is_self": False,
            "pe": peer.get("pe"),
            "pb": peer.get("pb"),
            "ev_ebitda": peer.get("ev_ebitda"),
            "roe": peer.get("roe"),
            "historical_pe": None,
            "consensus_upside": peer.get("upside"),
            "relative_score": _relative_score(peer_metrics, peer_ctx),
            "selection_reason": peer.get("peer_reason"),
        })
    rows.sort(key=lambda r: (-1 if r.get("relative_score") is None else -float(r["relative_score"])))
    return {
        "primary_metric": "pe",
        "rows": rows,
        "count": len(rows),
    }


def _explanation(symbol: str, valuation: dict[str, Any], sector_context: dict[str, Any]) -> dict[str, Any]:
    metrics = valuation.get("metrics") or {}
    context = valuation.get("context") or {}
    coverage = valuation.get("coverage") or {}
    company = valuation.get("company") or {}
    pe = (metrics.get("pe") or {}).get("value")
    pb = (metrics.get("pb") or {}).get("value")
    sector = company.get("sector") or "its sector"
    pe_ctx = context.get("pe") or {}
    pb_ctx = context.get("pb") or {}

    policy = valuation.get("policy") or {}
    if policy.get("primary_model"):
        current = (
            f"Primary valuation model for {symbol}: {policy['primary_model']}. "
            f"{policy.get('reason') or ''}"
        ).strip()
        if pe is not None and "pe" not in (policy.get("hidden_metrics") or []) and policy.get("primary_metric") == "pe":
            current += f" Trailing P/E {pe:.1f}x."
        elif pb is not None and policy.get("primary_metric") == "pb":
            current += f" Trailing P/B {pb:.1f}x."
    else:
        current = (
            f"{symbol} trades at "
            + (f"P/E {pe:.1f}x" if pe is not None else "an unavailable P/E")
            + (f" and P/B {pb:.1f}x" if pb is not None else "")
            + "."
        )
    hist_bits = []
    if pe_ctx.get("historical_median") is not None and pe is not None:
        hist_bits.append(
            f"P/E vs own history {pe:.1f}x vs median {pe_ctx['historical_median']:.1f}x"
            + (f" (percentile {pe_ctx.get('historical_percentile')})"
               if pe_ctx.get("historical_percentile") is not None else "")
        )
    if pb_ctx.get("historical_median") is not None and pb is not None:
        hist_bits.append(
            f"P/B vs own history {pb:.1f}x vs median {pb_ctx['historical_median']:.1f}x"
        )
    historical = "; ".join(hist_bits) + "." if hist_bits else "Historical valuation context is incomplete."

    peer_bits = []
    if pe_ctx.get("sector_median") is not None and pe is not None:
        pos = _position("pe", pe, pe_ctx["sector_median"])
        peer_bits.append(
            f"P/E sits {pos or 'near'} the {sector} median of {pe_ctx['sector_median']:.1f}x"
        )
    if sector_context.get("current_rank") and sector_context.get("universe"):
        peer_bits.append(
            f"rank {sector_context['current_rank']} of {sector_context['universe']} on "
            f"{sector_context.get('primary_metric', 'pe')}"
        )
    peer = "; ".join(peer_bits) + "." if peer_bits else "Peer context is limited by coverage."

    cov = (
        f"Engine coverage {coverage.get('pct', 0)}% "
        f"({coverage.get('available', 0)}/{coverage.get('applicable', 0)} applicable metrics)."
    )
    bottom = (
        "Read the multiples against history and peers; missing inputs are named "
        "rather than blank. This is valuation context, not a recommendation."
    )
    return {
        "current_valuation": current,
        "historical_context": historical,
        "peer_context": peer,
        "coverage": cov,
        "bottom_line": bottom,
        "sections": [
            {"title": "Current valuation", "text": current},
            {"title": "Historical context", "text": historical},
            {"title": "Peer context", "text": peer},
            {"title": "Coverage", "text": cov},
            {"title": "Bottom line", "text": bottom},
        ],
    }


def _flat_from_history_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pe": row.get("pe"),
        "pb": row.get("pb"),
        "ev_ebitda": row.get("ev_ebitda"),
        "ev_sales": row.get("ev_sales"),
        "ps": row.get("price_sales") or row.get("ps"),
        "dividend_yield": row.get("dividend_yield"),
        "market_cap": row.get("market_cap"),
        "enterprise_value": row.get("enterprise_value"),
        "cmp": row.get("price") or row.get("close"),
        "eps": row.get("eps"),
        "book_value_per_share": row.get("book_value"),
        "revenue": row.get("revenue"),
        "ebitda": row.get("ebitda"),
        "date": row.get("date"),
    }


def _flat_from_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {k: (v or {}).get("value") for k, v in metrics.items()}


def _change_log(
    symbol: str,
    metrics: dict[str, Any],
    history_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Yesterday → today attribution when two observations exist."""
    after = _flat_from_metrics(metrics)
    before = None
    before_date = None
    after_date = "today"
    if len(history_rows) >= 2:
        before = _flat_from_history_row(history_rows[-2])
        before_date = history_rows[-2].get("date")
    elif len(history_rows) == 1:
        before = _flat_from_history_row(history_rows[-1])
        before_date = history_rows[-1].get("date")

    if not before:
        return {
            "ok": True,
            "symbol": symbol,
            "changed": 0,
            "entries": [],
            "before_date": None,
            "after_date": after_date,
            "note": "Need at least two valuation observations for a change log.",
        }

    # Fill missing after inputs from latest history so attribution can compare.
    if history_rows:
        latest = _flat_from_history_row(history_rows[-1])
        for key, value in latest.items():
            if after.get(key) is None and value is not None:
                after[key] = value
        after_date = latest.get("date") or after_date

    log = attribution.change_log(before, after)
    # Also surface relative_score move if we can.
    return {
        "ok": True,
        "symbol": symbol,
        "before_date": before_date,
        "after_date": after_date,
        **{k: v for k, v in log.items() if k != "ok"},
    }


def _chart_coverage(symbol: str, window: str) -> dict[str, Any]:
    """Coverage summary for each chart metric (tab spans; points load on demand)."""
    from institutional_warehouse.history import SERIES, coverage as company_coverage

    win = _norm_window(window)
    cov = company_coverage(symbol)
    tabs = cov.get("tabs") or {}
    price_years = cov.get("price_years")
    out = {}
    for metric in CHART_METRICS:
        spec = SERIES.get(metric) or {}
        tab_id = spec.get("tab")
        tab = (tabs.get(tab_id) or {}) if tab_id else {}
        count = int(tab.get("rows") or 0)
        # Annual/ratio series span from fiscal endpoints, not price years.
        span = price_years if tab_id == "daily_market_history" or tab_id == "historical_valuation" else None
        out[metric] = {
            "ok": count > 0,
            "count": count,
            "first": tab.get("first"),
            "last": tab.get("last"),
            "observed_span": span,
            "confidence": _series_confidence(count, span),
            "tab": tab_id,
            "required_span_years": 10 if win == "10y" else (5 if win == "5y" else 3 if win == "3y" else 1),
        }
        out[metric]["sufficient_for_window"] = bool(
            count and (win == "max" or (span is not None and float(span) >= out[metric]["required_span_years"]))
        )
    return {
        "window": win,
        "windows": list(WINDOWS),
        "metrics": list(CHART_METRICS),
        "series": out,
        "tabs": tabs,
        "price_years": price_years,
    }


def _series_confidence(count: int, years: Optional[float]) -> str:
    if count >= 60 and (years or 0) >= 5:
        return "high"
    if count >= 20 and (years or 0) >= 2:
        return "moderate"
    if count > 0:
        return "low"
    return "none"


def _history_depth(history_rows: list[dict[str, Any]], charts: dict[str, Any]) -> tuple[Optional[float], int]:
    pe = ((charts.get("series") or {}).get("pe") or {})
    span = pe.get("observed_span")
    obs = int(pe.get("count") or len(history_rows) or 0)
    if span is None and len(history_rows) >= 2:
        # Rough span from dates YYYY-MM-DD
        try:
            from datetime import date
            first = str(history_rows[0].get("date") or "")[:10]
            last = str(history_rows[-1].get("date") or "")[:10]
            d0 = date.fromisoformat(first)
            d1 = date.fromisoformat(last)
            span = round((d1 - d0).days / 365.25, 2)
        except Exception:
            span = None
    return span, obs


def _overview(
    record: dict[str, Any],
    metrics: dict[str, Any],
    valuation: dict[str, Any],
    charts: dict[str, Any],
    confidence: dict[str, Any],
) -> dict[str, Any]:
    master = record.get("master") or {}
    price_meta = (valuation.get("provenance") or {}).get("price") or {}
    coverage = record.get("coverage") or {}
    return {
        "symbol": record.get("symbol"),
        "name": master.get("company_name") or record.get("symbol"),
        "cmp": (metrics.get("cmp") or {}).get("value"),
        "market_cap": (metrics.get("market_cap") or {}).get("value"),
        "sector": master.get("sector"),
        "industry": master.get("industry") or master.get("industry_dna"),
        "historical_coverage": (charts.get("series") or {}).get("pe", {}).get("count"),
        "consensus_coverage": bool((valuation.get("provenance") or {}).get("consensus", {}).get("source")),
        "updated": price_meta.get("updated_at"),
        "data_quality": confidence.get("band"),
        "health_score": confidence.get("score"),
        "warehouse_coverage": coverage,
    }


def _data_quality(symbol: str, record: dict[str, Any]) -> dict[str, Any]:
    """DQIV surface: validated / warnings / missing / conflicts / overrides."""
    from institutional_warehouse import db
    from institutional_warehouse.conflicts import recent as recent_conflicts

    conflicts = recent_conflicts(entity=symbol, limit=20)
    conflict_rows = conflicts.get("conflicts") or []
    try:
        override_count = db.count("wh_overrides", "entity = ?", (symbol,))
    except Exception:
        override_count = 0

    missing = []
    for key, label in (
        ("latest_price", "price"),
        ("latest_annual", "financials"),
        ("consensus", "consensus"),
        ("valuation", "historical_valuation"),
    ):
        if not record.get(key):
            missing.append(label)

    warnings: list[str] = []
    price = record.get("latest_price") or {}
    annual = record.get("latest_annual") or {}
    for row, name in ((price, "price"), (annual, "financials")):
        meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
        quality = meta.get("quality") or row.get("sys_quality")
        if quality and str(quality).lower() in {"warn", "warning", "fail"}:
            warnings.append(f"{name}: {quality}")

    freshness = _freshness(record)
    warnings.extend(freshness.get("warnings") or [])
    validated = not missing and not conflict_rows and not warnings
    return {
        "validated": validated,
        "warnings": warnings,
        "missing": missing,
        "conflicts": len(conflict_rows),
        "conflict_rows": conflict_rows[:5],
        "overrides": override_count,
        "freshness": freshness,
    }


def _freshness(record: dict[str, Any], *, now: Optional[datetime] = None) -> dict[str, Any]:
    """Turn timestamps into explicit terminal warnings; never silently imply live data."""
    now = now or datetime.now(timezone.utc)

    def age_hours(row: dict[str, Any]) -> Optional[float]:
        meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
        raw = meta.get("updated_at") or row.get("last_updated") or row.get("reported_time") or row.get("reported_date")
        if not raw:
            return None
        try:
            stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return max(0.0, (now - stamp.astimezone(timezone.utc)).total_seconds() / 3600)
        except (TypeError, ValueError):
            return None

    price_age = age_hours(record.get("latest_price") or {})
    financial_age = age_hours(record.get("latest_annual") or {})
    provider = record.get("provider_ratios") or {}
    ratio_age = age_hours({"reported_time": provider.get("as_of")})
    warnings = []
    # NSE cash session: 09:15–15:30 IST, Monday–Friday.  Outside it, one day
    # is acceptable; inside it, a 15-minute price is already stale.
    ist_hour = now.hour + 5 + (30 / 60)
    in_market = now.weekday() < 5 and 9.25 <= ist_hour <= 15.5
    price_limit = 0.25 if in_market else 24.0
    if price_age is None:
        warnings.append("price timestamp unavailable")
    elif price_age > price_limit:
        warnings.append(f"price stale ({price_age:.0f}h old)")
    if ratio_age is not None and ratio_age > 36:
        warnings.append(f"valuation ratios stale ({ratio_age:.0f}h old)")
    if financial_age is not None and financial_age > 24 * 180:
        warnings.append("financial statements older than 180 days")
    return {
        "price_age_hours": round(price_age, 1) if price_age is not None else None,
        "ratio_age_hours": round(ratio_age, 1) if ratio_age is not None else None,
        "financial_age_hours": round(financial_age, 1) if financial_age is not None else None,
        "price_fresh_limit_hours": price_limit,
        "warnings": warnings,
    }
