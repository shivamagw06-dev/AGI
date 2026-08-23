"""AGI Hedge Fund Intelligence Terminal.

An opportunity-first surface over the covered Indian equity universe. Every
strategy runs as a live scanner; the terminal ranks what came out of them,
records a daily snapshot so tomorrow can say what changed, and explains why
each company qualified. Descriptive research output only — never a call.
"""

from __future__ import annotations

import json
import os
import statistics as stats
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .live_alpha_bridge import (
    confluence_label,
    effective_agreement,
    fetch_live_alpha_rows,
    fundamental_bias,
    live_alpha_confirms,
    live_alpha_conflicts,
    unified_score,
)
from .scanner import (
    SOURCES,
    _SCANNERS,
    _base,
    _industry_medians,
    _median,
    _num,
    _primary_metric,
    _sane,
    _universe,
    market_regime,
    universe_meta,
    _suspect_multiple,
)

_SNAPSHOT_DAYS = 60
_INVENTORY_LIMIT = 1000


# ---------------------------------------------------------------------------
# Snapshot store — the only way the terminal can answer "what changed today?"
# ---------------------------------------------------------------------------
def store_root() -> Path:
    raw = (os.getenv("HEDGE_FUND_LAB_ROOT") or "").strip()
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "hedge_fund_lab"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "hedge_fund_lab"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _snap_path() -> Path:
    return store_root() / "snapshots.json"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_snapshots() -> dict[str, Any]:
    path = _snap_path()
    if not path.exists():
        return {"days": {}}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) and isinstance(data.get("days"), dict) else {"days": {}}
    except Exception:
        return {"days": {}}


def _save_snapshot(day: str, payload: dict[str, list[str]]) -> None:
    data = _load_snapshots()
    days = data.get("days") or {}
    days[day] = payload
    for stale in sorted(days)[:-_SNAPSHOT_DAYS]:
        days.pop(stale, None)
    data["days"] = days
    data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        _snap_path().write_text(json.dumps(data, indent=2, sort_keys=True))
    except Exception:
        pass


def _previous_day(day: str) -> Optional[str]:
    days = sorted((_load_snapshots().get("days") or {}).keys())
    prior = [d for d in days if d < day]
    return prior[-1] if prior else None


# ---------------------------------------------------------------------------
# Additional scanners
# ---------------------------------------------------------------------------
def _scan_growth(universe, medians, limit) -> list[dict[str, Any]]:
    """Earnings growth the market is already pricing, via the trailing-to-forward gap."""
    out = []
    for row in universe:
        pe, fwd = _sane(row, "pe"), _sane(row, "forward_pe")
        if pe is None or fwd is None or fwd <= 0:
            continue
        implied = round(((pe / fwd) - 1.0) * 100.0, 1)
        if implied < 25 or implied > 100:
            continue
        # Growth nobody covers and nobody can size is noise, not an idea.
        coverage = _num((row.get("consensus") or {}).get("coverage")) or 0
        if coverage < 5 and (_num(row.get("market_cap")) or 0) < 2e10:
            continue
        upside = _num((row.get("consensus") or {}).get("upside"))
        out.append(
            {
                **_base(row),
                "pe": pe,
                "forward_pe": fwd,
                "implied_earnings_growth_pct": implied,
                "why": (
                    f"Trailing P/E of {pe} against a forward P/E of {fwd} implies {implied}% "
                    "earnings growth is already in the price"
                    + (f", alongside {upside}% consensus upside." if upside is not None else ".")
                    + " The research question is whether the growth is deliverable, not whether it is expected."
                ),
            }
        )
    out.sort(key=lambda r: -r["implied_earnings_growth_pct"])
    return out[:limit]


def _scan_dividend(universe, medians, limit) -> list[dict[str, Any]]:
    """Yield that profitability and leverage can plausibly support."""
    out = []
    for row in universe:
        yld = _sane(row, "dividend_yield")
        roe = _sane(row, "roe")
        debt = _sane(row, "debt_to_equity")
        if yld is None or yld < 2.0 or yld > 12.0:
            continue
        if roe is not None and roe < 8:
            continue
        if debt is not None and debt > 200:
            continue
        out.append(
            {
                **_base(row),
                "dividend_yield": yld,
                "roe": roe,
                "debt_to_equity": debt,
                "why": (
                    f"Yields {yld}%"
                    + (f" on a {roe}% return on equity" if roe is not None else "")
                    + (f" with debt/equity at {debt}" if debt is not None else "")
                    + " — income supported by returns rather than by a falling share price."
                    + (
                        " Verify the payout is recurring: yields this high often include a special dividend."
                        if yld > 8
                        else ""
                    )
                ),
            }
        )
    out.sort(key=lambda r: -r["dividend_yield"])
    return out[:limit]


def _scan_live_alpha(universe, medians, limit) -> list[dict[str, Any]]:
    """Ninth scanner — intraday Live Alpha engines (research-only)."""
    del universe, medians  # Live Alpha reads Supabase, not the warehouse scan.
    fetched = fetch_live_alpha_rows(limit=limit)
    if not fetched.get("ok"):
        return []
    return list(fetched.get("rows") or [])


SCANS: dict[str, tuple[str, Callable]] = {
    **{k: v for k, v in _SCANNERS.items()},
    "growth": ("Forward Earnings Growth", _scan_growth),
    "dividend": ("Dividend / income", _scan_dividend),
    "live_alpha": ("Live Alpha confirmation", _scan_live_alpha),
}

# Fundamentals-first desk with Live Alpha as the ninth independent scanner.
_ORDER = ["alpha", "value", "quality", "growth", "conviction", "dividend", "stress", "pairs", "live_alpha"]

_SCAN_QUALIFICATION = {
    "alpha": ("candidate", "Candidate"),
    "value": ("operational", "Operational scanner"),
    "quality": ("operational", "Operational scanner"),
    "growth": ("operational", "Operational scanner"),
    "conviction": ("operational", "Operational scanner"),
    "dividend": ("operational", "Operational scanner"),
    "stress": ("operational", "Operational scanner"),
    "pairs": ("candidate", "Production candidate scanner"),
    "live_alpha": ("candidate", "Live Alpha confirmation — warming up"),
}

_SCAN_PROFILE: dict[str, dict[str, str]] = {
    "alpha": {
        "alpha": "Agreement across value, financial quality, growth and earnings consensus",
        "risk": "Medium — a composite prioritises research; it cannot replace catalyst and downside work",
        "question": "Which component is genuinely differentiated, and what could invalidate the combined signal?",
    },
    "value": {
        "alpha": "Multiple re-rating toward the industry median",
        "risk": "Medium — cheap can stay cheap when returns are structurally lower",
        "question": "Is the discount a mispricing or a verdict?",
    },
    "quality": {
        "alpha": "Compounding returns on capital held through cycles",
        "risk": "Low to medium — the usual failure is overpaying",
        "question": "Is the return on capital durable, and what is priced for it?",
    },
    "growth": {
        "alpha": "Forward EPS delivery against the trailing-to-forward P/E gap",
        "risk": "High — de-rating is violent when growth disappoints",
        "question": "Can the implied forward EPS growth actually be delivered? This is not a revenue or historical CAGR screen.",
    },
    "conviction": {
        "alpha": "Sell-side expectation gaps that resolve on results",
        "risk": "Medium — consensus is an expectation to test, not a signal",
        "question": "What does the street assume, and is it defensible?",
    },
    "dividend": {
        "alpha": "Cash return supported by profitability",
        "risk": "Low to medium — yield traps appear when the price is falling for a reason",
        "question": "Is the payout covered through a downturn?",
    },
    "stress": {
        "alpha": "Dislocation from forced selling and balance-sheet repair",
        "risk": "Very high — permanent capital loss is the base case if wrong",
        "question": "Is this a solvency problem or a liquidity problem?",
    },
    "pairs": {
        "alpha": "Convergence of a valuation gap between industry peers",
        "risk": "Medium — the spread widens before it converges, if it converges",
        "question": "Is the gap explained by profitability, or is it mispricing?",
    },
    "live_alpha": {
        "alpha": "Intraday leadership, activity, breakout, dislocation and positioning",
        "risk": "High — tactical signals can conflict with slower fundamental screens",
        "question": "Does today's market behaviour confirm or contradict the fundamental case?",
    },
}


# ---------------------------------------------------------------------------
# Confidence — a bounded, explainable score, never a probability of profit
# ---------------------------------------------------------------------------
def _confidence(key: str, row: dict[str, Any]) -> int:
    def clamp(x: float) -> int:
        return int(max(25, min(95, round(x))))

    if key == "alpha":
        base = 35 + (_num(row.get("alpha_opportunity_score")) or 0) * 0.55
        base += min(12, len(row.get("factor_scores") or {}) * 3)
        if row.get("risk_flags"):
            base -= 15
        return clamp(base)
    if key == "value":
        base = 45 + abs(_num(row.get("discount_pct")) or 0) / 2.0
        if row.get("classification") == "Potential value trap":
            base -= 20
        return clamp(base)
    if key == "quality":
        return clamp(35 + (_num(row.get("quality_score")) or 0) * 0.7)
    if key == "growth":
        return clamp(40 + (_num(row.get("implied_earnings_growth_pct")) or 0) / 3.0)
    if key == "momentum":
        return clamp(45 + (_num(row.get("relative_strength")) or 0) / 2.5)
    if key == "technical":
        return clamp(30 + (_num(row.get("technical_score")) or 0) * 0.65)
    if key == "conviction":
        return clamp(
            (_num(row.get("buy_share_pct")) or 0) * 0.5
            + (_num(row.get("consensus_upside")) or 0) * 0.8
        )
    if key == "dividend":
        return clamp(40 + (_num(row.get("dividend_yield")) or 0) * 6.0)
    if key == "stress":
        return clamp(50 + len(row.get("stress_flags") or []) * 12)
    if key == "pairs":
        return clamp(30 + (_num(row.get("spread_multiple")) or 0) * 12)
    if key == "live_alpha":
        return clamp(35 + (_num(row.get("live_alpha_score")) or 0) * 0.65)
    return 50


def _identity(row: dict[str, Any]) -> tuple[str, str]:
    """Ticker and display name for a scan row, whether single-name or a pair."""
    if row.get("long_leg"):
        leg = row["long_leg"]
        return str(leg.get("ticker") or ""), str(leg.get("company_name") or leg.get("ticker") or "")
    return str(row.get("ticker") or ""), str(row.get("company_name") or row.get("ticker") or "")


def run_all(limit: int = 12) -> dict[str, Any]:
    universe = _universe()
    if not universe:
        return {"ok": False, "error": "universe_empty"}
    medians = _industry_medians(universe)
    results: dict[str, list[dict[str, Any]]] = {}
    for key in _ORDER:
        label, fn = SCANS[key]
        rows = fn(universe, medians, limit)
        for row in rows:
            row["confidence"] = _confidence(key, row)
            row["strategy"] = key
            row["strategy_label"] = label
        results[key] = rows
    return {
        "ok": True,
        "universe": universe,
        "medians": medians,
        "results": results,
        "universe_meta": universe_meta(),
    }


def record_daily_snapshot(*, limit: int = 1000) -> dict[str, Any]:
    """Persist today's scanner hits after the warehouse refresh.

    The Hedge Fund page day-on-day strip reads this file. Calling it from the
    nightly refresh means the page updates itself without waiting for a visit.
    """
    run = run_all(limit=limit)
    if not run.get("ok"):
        return {"ok": False, "error": run.get("error") or "universe_empty", "skipped": True}
    day = _today()
    snapshot = {
        key: [_identity(r)[0] for r in rows if _identity(r)[0]]
        for key, rows in (run.get("results") or {}).items()
    }
    _save_snapshot(day, snapshot)
    meta = universe_meta()
    return {
        "ok": True,
        "as_of": day,
        "universe_scanned": len(run.get("universe") or []),
        "strategies": {k: len(v) for k, v in snapshot.items()},
        "universe_meta": meta,
        "sources": dict(SOURCES),
    }


# ---------------------------------------------------------------------------
# Market regime, extended with rotation and sentiment
# ---------------------------------------------------------------------------
def regime(universe: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    base = market_regime()
    rows = universe if universe is not None else _universe()
    if not base.get("ok") or not rows:
        return base

    sectors: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sector = row.get("primary_sector")
        if sector:
            sectors.setdefault(sector, []).append(row)

    sector_rows = []
    for sector, members in sectors.items():
        if len(members) < 5:
            continue
        upside = _median([(m.get("consensus") or {}).get("upside") for m in members])
        sector_rows.append(
            {
                "sector": sector,
                "companies": len(members),
                "median_pe": _median([_sane(m, "pe") for m in members]),
                "median_roe": _median([_sane(m, "roe") for m in members]),
                "median_return_1y": _median([(m.get("consensus") or {}).get("return_1y") for m in members]),
                "median_consensus_upside": upside,
            }
        )
    ranked = [s for s in sector_rows if s["median_consensus_upside"] is not None]
    ranked.sort(key=lambda s: -(s["median_consensus_upside"] or 0))

    returns = [
        _num((r.get("consensus") or {}).get("return_1y"))
        for r in rows
        if _num((r.get("consensus") or {}).get("return_1y")) is not None
    ]
    advancing = sum(1 for r in returns if r > 0)
    declining = max(1, len(returns) - advancing)
    ad_ratio = round(advancing / declining, 2) if returns else None

    median_pe = base.get("median_pe")
    if median_pe is None:
        valuation = "Unknown"
    elif median_pe >= 32:
        valuation = "Expensive"
    elif median_pe >= 22:
        valuation = "Full"
    elif median_pe >= 15:
        valuation = "Fair"
    else:
        valuation = "Cheap"

    upside = base.get("median_consensus_upside_pct")
    if upside is None:
        sentiment = "Unknown"
    elif upside >= 20:
        sentiment = "Constructive"
    elif upside >= 8:
        sentiment = "Balanced"
    elif upside >= 0:
        sentiment = "Cautious"
    else:
        sentiment = "Defensive"

    dispersion = None
    if len(returns) > 10:
        dispersion = round(stats.pstdev(returns), 1)

    return {
        **base,
        "advance_decline_ratio": ad_ratio,
        "advancing": advancing,
        "declining": len(returns) - advancing,
        "valuation_stance": valuation,
        "institutional_sentiment": sentiment,
        "return_dispersion_pct": dispersion,
        "sector_rotation": {
            "most_attractive": ranked[0] if ranked else None,
            "least_attractive": ranked[-1] if ranked else None,
            "ranked": ranked[:12],
        },
        "vix": None,
        "vix_note": "India VIX is not wired into this engine yet; dispersion of one-year returns is shown instead.",
    }


# ---------------------------------------------------------------------------
# The terminal overview — everything the page needs in one call
# ---------------------------------------------------------------------------
_OVERVIEW_CACHE: dict[str, Any] = {"key": None, "at": 0.0, "payload": None}
_OVERVIEW_TTL_SEC = 180.0
_OVERVIEW_LOCK = None


def _overview_lock():
    """Lazy lock so concurrent terminal requests share one cold build."""
    global _OVERVIEW_LOCK
    if _OVERVIEW_LOCK is None:
        import threading

        _OVERVIEW_LOCK = threading.Lock()
    return _OVERVIEW_LOCK


def overview(limit: int = 12) -> dict[str, Any]:
    """Build the hedge-fund terminal. Cached + single-flight on cold miss."""
    import time

    capped = max(1, min(int(limit or 12), 50))
    now = time.time()
    cache_key = f"limit:{capped}"
    cached = _OVERVIEW_CACHE.get("payload")
    if (
        cached
        and _OVERVIEW_CACHE.get("key") == cache_key
        and (now - float(_OVERVIEW_CACHE.get("at") or 0.0)) < _OVERVIEW_TTL_SEC
    ):
        out = dict(cached)
        out["cache"] = {"hit": True, "ttl_sec": _OVERVIEW_TTL_SEC}
        return out

    with _overview_lock():
        # Re-check after waiting — another request may have filled the cache.
        now = time.time()
        cached = _OVERVIEW_CACHE.get("payload")
        if (
            cached
            and _OVERVIEW_CACHE.get("key") == cache_key
            and (now - float(_OVERVIEW_CACHE.get("at") or 0.0)) < _OVERVIEW_TTL_SEC
        ):
            out = dict(cached)
            out["cache"] = {"hit": True, "ttl_sec": _OVERVIEW_TTL_SEC, "single_flight": True}
            return out
        return _overview_uncached(capped, cache_key, now)


def _overview_uncached(capped: int, cache_key: str, now: float) -> dict[str, Any]:
    full_run = run_all(limit=_INVENTORY_LIMIT)
    if not full_run.get("ok"):
        return {"ok": False, "error": full_run.get("error") or "universe_empty", "cache": {"hit": False}}

    universe = full_run["universe"]
    medians = full_run["medians"]
    full_results = full_run["results"]
    # Display respects the UI cap; inventory comparison uses complete scanner membership.
    results = {key: (rows or [])[:capped] for key, rows in full_results.items()}

    day = _today()
    membership_snapshot = {
        key: [_identity(r)[0] for r in rows if _identity(r)[0]]
        for key, rows in full_results.items()
    }
    prior_day = _previous_day(day)
    prior = (_load_snapshots().get("days") or {}).get(prior_day) or {} if prior_day else {}
    _save_snapshot(day, membership_snapshot)

    live_alpha_by_ticker: dict[str, dict[str, Any]] = {}
    for row in full_results.get("live_alpha") or []:
        ticker = str(row.get("ticker") or "").upper()
        if ticker:
            live_alpha_by_ticker[ticker] = row

    # Strategy suitability comes from the regime, keyed onto the scanners.
    reg = regime(universe)
    suitability_by_name = {s["strategy"]: s for s in (reg.get("strategy_suitability") or [])}
    suitability_map = {
        "alpha": "Long / Short Equity",
        "value": "Value / Deep Value",
        "quality": "Long / Short Equity",
        "growth": "Long / Short Equity",
        "technical": "Momentum / CTA Trend",
        "momentum": "Momentum / CTA Trend",
        "conviction": "Long / Short Equity",
        "dividend": "Equity Market Neutral",
        "stress": "Distressed",
        "pairs": "Equity Market Neutral",
        "live_alpha": "Momentum / CTA Trend",
    }
    from reliability_registry import component as reliability_component
    from strategy_lab.governance_view import governance_for

    cards = []
    new_today: list[dict[str, Any]] = []
    removed_today: list[dict[str, Any]] = []
    for key in _ORDER:
        rows = results[key]
        label = SCANS[key][0]
        confs = [r.get("confidence") for r in rows if r.get("confidence")]
        current = set(membership_snapshot.get(key) or [])
        previous = set(prior.get(key) or [])
        entered = sorted(current - previous) if prior else []
        exited = sorted(previous - current) if prior else []
        profile = _SCAN_PROFILE.get(key, {})
        suit = suitability_by_name.get(suitability_map.get(key, ""), {})
        reliability_record = reliability_component(key)
        for ticker in entered:
            row = next((r for r in rows if _identity(r)[0] == ticker), None)
            new_today.append(
                {"ticker": ticker, "company_name": _identity(row)[1] if row else ticker,
                 "strategy": key, "strategy_label": label, "why": (row or {}).get("why")}
            )
        for ticker in exited:
            removed_today.append({"ticker": ticker, "strategy": key, "strategy_label": label})
        cards.append(
            {
                "id": key,
                "label": label,
                "count": len(rows),
                "avg_confidence": round(sum(confs) / len(confs), 1) if confs else None,
                "suitability_stars": suit.get("stars"),
                "suitability_why": suit.get("why"),
                "alpha_source": profile.get("alpha"),
                "risk_level": profile.get("risk"),
                "research_question": profile.get("question"),
                "qualification_status": reliability_record["lifecycle"],
                "qualification_label": reliability_record["lifecycle_label"],
                "operational": reliability_record["lifecycle"] == "operational",
                "research_validated": False,
                "investment_validated": False,
                "production_validated": False,
                "backtest_status": "not_backtested",
                "reliability": reliability_record,
                "governance": governance_for(key),
                "entered_today": len(entered),
                "exited_today": len(exited),
                # Embed preview rows so the UI does not re-scan on first paint.
                "results": rows,
            }
        )

    # Strategy overlap — independent scanners agreeing on the same company.
    overlap: dict[str, dict[str, Any]] = {}
    for key, rows in full_results.items():
        if key == "live_alpha":
            continue
        for row in rows:
            ticker, name = _identity(row)
            if not ticker:
                continue
            entry = overlap.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "company_name": name,
                    "sector": row.get("sector") or (row.get("long_leg") or {}).get("sector"),
                    "industry": row.get("industry") or (row.get("long_leg") or {}).get("industry"),
                    "market_cap": row.get("market_cap") or (row.get("long_leg") or {}).get("market_cap"),
                    "coverage": row.get("coverage") or (row.get("long_leg") or {}).get("coverage"),
                    "fundamental_strategies": [],
                    "fundamental_confidences": [],
                },
            )
            entry["fundamental_strategies"].append(SCANS[key][0])
            entry["fundamental_confidences"].append(row.get("confidence") or 50)

    for ticker, la in live_alpha_by_ticker.items():
        overlap.setdefault(
            ticker,
            {
                "ticker": ticker,
                "company_name": la.get("company_name") or ticker,
                "sector": la.get("sector"),
                "industry": None,
                "market_cap": None,
                "coverage": None,
                "fundamental_strategies": [],
                "fundamental_confidences": [],
            },
        )

    overlap_rows = []
    for ticker, entry in overlap.items():
        fund_n = len(entry["fundamental_strategies"])
        fund_confidences = entry["fundamental_confidences"]
        fund_avg = round(sum(fund_confidences) / fund_n, 1) if fund_n else None
        la = live_alpha_by_ticker.get(ticker)
        la_present = la is not None
        la_direction = la.get("direction") if la else None
        hfl_bias = fundamental_bias(fund_avg)
        confirms = live_alpha_confirms(hfl_bias=hfl_bias, live_direction=la_direction)
        conflicts = live_alpha_conflicts(hfl_bias=hfl_bias, live_direction=la_direction)
        agreement = effective_agreement(fundamental_count=fund_n, live_alpha_confirms=confirms)
        display_strategies = list(entry["fundamental_strategies"])
        if la_present:
            display_strategies.append("Live Alpha")
        label = confluence_label(
            hfl_scanner_count=fund_n,
            live_alpha_present=la_present,
            live_direction=la_direction,
            hfl_bias=hfl_bias,
        )
        unified = unified_score(
            hfl_score=fund_avg or 50.0,
            live_alpha_score=(la or {}).get("live_alpha_score"),
            live_direction=la_direction,
            hfl_bias=hfl_bias,
        )
        overlap_rows.append(
            {
                "ticker": entry["ticker"],
                "company_name": entry["company_name"],
                "sector": entry["sector"],
                "industry": entry["industry"],
                "market_cap": entry["market_cap"],
                "coverage": entry["coverage"],
                "strategies": display_strategies,
                "fundamental_strategies": entry["fundamental_strategies"],
                "agreement": agreement,
                "fundamental_agreement": fund_n,
                "avg_confidence": fund_avg,
                "fundamental_confidence": fund_avg,
                "priority_score": round(unified, 1),
                "unified_score": unified,
                "confluence_label": label,
                "live_alpha_confirms": confirms,
                "live_alpha_conflicts": conflicts,
                "live_alpha": {
                    "present": la_present,
                    "direction": la_direction,
                    "score": (la or {}).get("live_alpha_score"),
                    "signed_score": (la or {}).get("live_alpha_signed"),
                    "engine_agreement": (la or {}).get("engine_agreement"),
                    "contributing_engines": (la or {}).get("contributing_engines") or [],
                    "signal_age_minutes": (la or {}).get("signal_age_minutes"),
                    "newest_signal_at": (la or {}).get("newest_signal_at"),
                    "confirms": confirms,
                    "conflicts": conflicts,
                } if la_present else None,
            }
        )
    overlap_rows.sort(key=lambda r: -r["priority_score"])

    # Research priority queue — where an analyst should spend the morning.
    # Microcaps clear these screens easily; the queue favours names an
    # institution could actually take a position in.
    _SIZE_FLOOR = 2e10  # roughly Rs 2,000 crore
    agreed = [r for r in overlap_rows if r["agreement"] >= 2]
    investable = [
        r for r in agreed
        if (r.get("market_cap") or 0) >= _SIZE_FLOOR or (r.get("coverage") or 0) >= 5
    ]
    ranked_queue = investable if len(investable) >= 5 else agreed

    queue = []
    for rank, row in enumerate(ranked_queue[:10], start=1):
        minutes = 30 + 15 * min(4, row["agreement"])
        la = row.get("live_alpha") or {}
        fund_strategies = row.get("fundamental_strategies") or []
        why_parts = [
            f"{row['fundamental_agreement']} fundamental scanner"
            f"{'s' if row['fundamental_agreement'] != 1 else ''}: "
            + ", ".join(fund_strategies),
        ]
        if la.get("confirms"):
            why_parts.append(
                f"Live Alpha confirms ({la.get('direction') or '—'})"
                + (f" via {', '.join(la.get('contributing_engines') or [])}" if la.get("contributing_engines") else "")
            )
        elif la.get("conflicts"):
            why_parts.append(f"Live Alpha timing conflict ({la.get('direction') or '—'} vs fundamentals)")
        elif la.get("present"):
            why_parts.append(f"Live Alpha present ({la.get('direction') or '—'}) — not counted as agreement")
        queue.append(
            {
                "rank": rank,
                "ticker": row["ticker"],
                "company_name": row["company_name"],
                "sector": row["sector"],
                "industry": row["industry"],
                "stars": max(1, min(5, 1 + row["agreement"])),
                "why": " · ".join(why_parts),
                "estimated_research_minutes": minutes,
                "confidence": row.get("fundamental_confidence"),
                "unified_score": row.get("unified_score"),
                "confluence_label": row.get("confluence_label"),
                "live_alpha_direction": la.get("direction"),
                "live_alpha_engines": la.get("contributing_engines") or [],
                "signal_age_minutes": la.get("signal_age_minutes"),
                "engine_agreement": la.get("engine_agreement"),
                "market_cap": row.get("market_cap"),
                "strategies": row["strategies"],
            }
        )

    def _top(key: str) -> Optional[dict[str, Any]]:
        rows = results.get(key) or []
        sized = [
            r for r in rows
            if (r.get("market_cap") or (r.get("long_leg") or {}).get("market_cap") or 0) >= 2e10
            or (r.get("coverage") or (r.get("long_leg") or {}).get("coverage") or 0) >= 5
        ]
        pool = sized or rows
        return pool[0] if pool else None

    highlights = [
        {"label": "Highest conviction", "scan": "conviction", "row": _top("conviction")},
        {"label": "Largest headline discount", "scan": "value", "row": _top("value")},
        {"label": "Highest quality", "scan": "quality", "row": _top("quality")},
        {"label": "Strongest momentum", "scan": "momentum", "row": _top("momentum")},
        {"label": "Widest valuation dispersion", "scan": "pairs", "row": _top("pairs")},
    ]

    total = sum(len(rows) for rows in results.values())
    live_meta = fetch_live_alpha_rows(limit=1).get("meta") or {}
    forecast_intelligence = _forecast_intelligence_status()
    reliability = _reliability_status(
        universe_count=len(universe), live_meta=live_meta,
        forecast_intelligence=forecast_intelligence,
    )
    payload = {
        "ok": True,
        "as_of": day,
        "compared_with": prior_day,
        "regime": reg,
        "hero": {
            "universe_scanned": len(universe),
            "strategies_running": sum(1 for key in _ORDER if reliability_component(key)["lifecycle"] == "operational"),
            "research_modules": len(_ORDER),
            "live_opportunities": total,
            "companies_flagged": len(overlap_rows),
            "multi_strategy_companies": sum(1 for r in overlap_rows if r["agreement"] >= 2),
            "live_alpha_qualifying": live_meta.get("qualifying_symbols"),
            "highlights": [h for h in highlights if h["row"]],
        },
        "cards": cards,
        "overlap": overlap_rows[:20],
        "research_queue": queue,
        "market_dashboard": market_dashboard(universe, medians),
        "factors": factor_dashboard(universe, medians),
        "daily_intelligence": {
            "baseline": prior_day is None,
            "new_opportunities": new_today[:20],
            "removed_opportunities": removed_today[:20],
            "note": (
                "First snapshot recorded today — day-on-day changes appear from the next run."
                if prior_day is None
                else f"Compared with the scan recorded on {prior_day}."
            ),
        },
        "sources": dict(SOURCES),
        "universe_meta": universe_meta(),
        "policy": "Research observations only — no buy, sell, target price or personalised advice.",
        "live_alpha_meta": live_meta,
        "institutional_stack": {
            "strategy_library": {
                "count": 8,
                "methodologies": [
                    "Long / Short Equity", "Equity Market Neutral", "Statistical Arbitrage",
                    "Global Macro", "Merger Arbitrage", "Convertible Arbitrage",
                    "CTA / Managed Futures", "Distressed & Special Situations",
                ],
            },
            "research_scanners": {
                "count": len(_ORDER),
                "operational": sum(1 for key in _ORDER if reliability_component(key)["lifecycle"] == "operational"),
                "experimental": sum(1 for key in _ORDER if reliability_component(key)["lifecycle"] == "experimental"),
            },
            "live_alpha": {
                "engines": ["Leadership", "Activity", "Breakout", "Dislocation", "Positioning"],
                "qualifying_symbols": live_meta.get("qualifying_symbols"),
                "freshness": live_meta.get("freshness_mode") or "session",
                "status": "active" if live_meta.get("qualifying_symbols") else "waiting_for_qualifying_signals",
            },
            "alpha_opportunity": {
                "companies_flagged": len(overlap_rows),
                "multi_strategy_companies": sum(1 for r in overlap_rows if r["agreement"] >= 2),
                "queue_size": len(queue),
                "status": "active" if overlap_rows else "waiting_for_scanner_results",
            },
            "forecast_intelligence": forecast_intelligence,
        },
        "reliability_registry": reliability,
        "scoring": {
            "unified_weights": {"hedge_fund": 0.7, "live_alpha": 0.3},
            "weighting_status": "agi_designed_not_empirically_optimized",
            "weighting_label": "AGI composite weighting",
            "hedge_fund_component": "fundamental scanner confidence only (excludes Live Alpha)",
            "agreement_rule": "Live Alpha increases agreement only on directional confirmation",
            "conflict_penalty": "Negative Live Alpha conflicts reduce the unified score instead of adding agreement.",
            "freshness": live_meta.get("freshness_mode") or "session",
        },
        "validation_lifecycle": {
            "operational": "Code runs and required data is available.",
            "research_validated": "Requires a costed point-in-time backtest, liquidity checks and out-of-sample validation.",
            "investment_validated": "Requires robust risk-adjusted performance across regimes and a documented failure profile.",
            "current_operational_scanners": sum(
                1 for key in _ORDER if reliability_component(key)["lifecycle"] == "operational"
            ),
            "current_research_validated_strategies": 0,
            "current_investment_validated_strategies": 0,
        },
        "cache": {"hit": False, "ttl_sec": _OVERVIEW_TTL_SEC},
    }
    _OVERVIEW_CACHE["key"] = cache_key
    _OVERVIEW_CACHE["at"] = now
    _OVERVIEW_CACHE["payload"] = payload
    return payload


def _reliability_status(*, universe_count: int, live_meta: dict[str, Any], forecast_intelligence: dict[str, Any]) -> dict[str, Any]:
    from reliability_registry import registry

    overrides: dict[str, dict[str, Any]] = {}
    if universe_count <= 0:
        for key in ("value", "quality", "growth", "conviction", "dividend", "alpha", "pairs", "stress"):
            overrides[key] = {"health": "failed", "health_reason": "Warehouse strategy universe is empty."}
    if not live_meta.get("qualifying_symbols"):
        overrides["live_alpha"] = {
            "health": "degraded",
            "health_reason": "No fresh, liquid, quality-qualified Live Alpha signals are currently available.",
            "evidence": {"qualifying_symbols": live_meta.get("qualifying_symbols") or 0},
        }
    if not forecast_intelligence.get("company_forecasts"):
        overrides["fie"] = {"health": "degraded", "health_reason": "No stored company forecasts are available."}
    if not forecast_intelligence.get("outcome_evaluations"):
        overrides["fle"] = {
            "health": "degraded",
            "health_reason": "Outcome evaluation framework is operational but empirical outcomes have not accumulated.",
        }
    return registry(overrides)


def reliability_status() -> dict[str, Any]:
    """Registry view with current data availability, independent of terminal success."""
    try:
        universe_count = int(universe_meta().get("count") or 0)
        if universe_count <= 0:
            universe_count = len(_universe())
    except Exception:
        universe_count = 0
    live_meta = fetch_live_alpha_rows(limit=1).get("meta") or {}
    forecast_intelligence = _forecast_intelligence_status()
    out = _reliability_status(
        universe_count=universe_count,
        live_meta=live_meta,
        forecast_intelligence=forecast_intelligence,
    )
    out["runtime_evidence"] = {
        "strategy_universe": universe_count,
        "live_alpha_qualifying": live_meta.get("qualifying_symbols") or 0,
        "forecast_company": forecast_intelligence.get("company_forecasts") or 0,
        "forecast_evaluations": forecast_intelligence.get("outcome_evaluations") or 0,
    }
    return out


def _forecast_intelligence_status() -> dict[str, Any]:
    """Cheap warehouse status for the FIE/FLE layer shown in Hedge Fund Lab."""
    counts: dict[str, int] = {}
    try:
        from institutional_warehouse import store

        for tab in (
            "forecast_company", "forecast_metric_predictions", "forecast_snapshots",
            "forecast_evaluations", "forecast_accuracy", "forecast_learnings",
        ):
            page = store.fetch(tab, limit=1)
            counts[tab] = int(page.get("total") or 0)
    except Exception:
        counts = {}
    forecasts = counts.get("forecast_company", 0)
    evaluations = counts.get("forecast_evaluations", 0)
    accuracy = counts.get("forecast_accuracy", 0)
    return {
        "engine": "FIE 8.5 + FLE Phase 1",
        "status": "measuring_outcomes" if evaluations else ("forecasting" if forecasts else "waiting_for_forecasts"),
        "company_forecasts": forecasts,
        "metric_predictions": counts.get("forecast_metric_predictions", 0),
        "immutable_snapshots": counts.get("forecast_snapshots", 0),
        "outcome_evaluations": evaluations,
        "accuracy_records": accuracy,
        "validated_learnings": counts.get("forecast_learnings", 0),
        "self_learning_claim": False,
        "governance": "Only validated outcomes feed accuracy; model parameters are not changed automatically.",
    }


def market_dashboard(universe=None, medians=None) -> dict[str, Any]:
    rows = universe if universe is not None else _universe()
    if not rows:
        return {"ok": False, "error": "universe_empty"}
    meds = medians if medians is not None else _industry_medians(rows)

    sectors: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sector = row.get("primary_sector")
        if sector:
            sectors.setdefault(sector, []).append(row)

    sector_rows = []
    for sector, members in sectors.items():
        if len(members) < 5:
            continue
        sector_rows.append(
            {
                "sector": sector,
                "companies": len(members),
                "median_pe": _median([_sane(m, "pe") for m in members]),
                "median_pb": _median([_sane(m, "pb") for m in members]),
                "median_roe": _median([_sane(m, "roe") for m in members]),
                "median_yield": _median([_sane(m, "dividend_yield") for m in members]),
                "median_return_1y": _median([(m.get("consensus") or {}).get("return_1y") for m in members]),
                "median_upside": _median([(m.get("consensus") or {}).get("upside") for m in members]),
            }
        )

    priced = [s for s in sector_rows if s["median_pe"] is not None]
    priced.sort(key=lambda s: s["median_pe"])

    # Premium and discount against the company's own industry.
    gaps = []
    for row in rows:
        industry = row.get("primary_industry")
        med = (meds.get(industry) or {})
        if (med.get("count") or 0) < 5:
            continue
        metric = _primary_metric(row.get("industry_dna"))
        value, benchmark = _sane(row, metric), _num(med.get(metric))
        if value is None or not benchmark or value <= 0:
            continue
        gaps.append(
            {
                **_base(row),
                "metric": metric,
                "value": value,
                "industry_median": benchmark,
                "gap_pct": round(((value / benchmark) - 1.0) * 100.0, 1),
                "relative_multiple": round(value / benchmark, 2),
                # Flag on the evidence, not on the metric name — see
                # hedge_fund_lab.scanner._SUSPECT_BELOW.
                "validation_status": "normalization_required" if _suspect_multiple(metric, value)
                or abs(((value / benchmark) - 1.0) * 100.0) >= 300 else "screen_validated",
            }
        )
    gaps.sort(key=lambda r: r["gap_pct"])

    def _rank(field: str, reverse: bool, n: int = 5) -> list[dict[str, Any]]:
        vals = [(row, _sane(row, field)) for row in rows]
        vals = [(row, v) for row, v in vals if v is not None]
        vals.sort(key=lambda pair: -pair[1] if reverse else pair[1])
        return [{**_base(row), field: v} for row, v in vals[:n]]

    conviction = [
        {**_base(row), "upside": _num((row.get("consensus") or {}).get("upside")),
         "coverage": _num((row.get("consensus") or {}).get("coverage"))}
        for row in rows
        if _num((row.get("consensus") or {}).get("upside")) is not None
        and (_num((row.get("consensus") or {}).get("coverage")) or 0) >= 10
    ]
    conviction.sort(key=lambda r: -(r["upside"] or 0))

    return {
        "ok": True,
        "sectors": sector_rows,
        "lowest_median_pe_sector": priced[0] if priced else None,
        "highest_median_pe_sector": priced[-1] if priced else None,
        # Compatibility aliases; the UI must not describe these as attractiveness rankings.
        "cheapest_sector": priced[0] if priced else None,
        "most_expensive_sector": priced[-1] if priced else None,
        "largest_discounts": gaps[:5],
        "largest_premiums": list(reversed(gaps[-5:])) if gaps else [],
        "highest_roe": _rank("roe", True),
        "highest_yield": _rank("dividend_yield", True),
        "highest_conviction": conviction[:5],
        "methodology": {
            "definition": "Median constituent trailing P/E by sector",
            "formula": "median of valid positive constituent P/E observations",
            "period": universe_meta().get("as_of"),
            "universe": "covered warehouse companies grouped by primary sector",
            "exclusions": "missing, negative and out-of-bounds P/E; sectors with fewer than five covered companies",
            "source": SOURCES["market_data"],
            "weighting": "equal-weighted median; not market-cap weighted",
            "accounting": "reported trailing valuation metrics; consolidated scope where supplied by the warehouse, otherwise scope is disclosed as unavailable",
            "liquidity_rule": "none beyond valid stored market observations; no minimum market-cap filter",
            "financial_company_treatment": "sector medians retain financial companies; EV/EBITDA is not used for banks and insurers",
        },
        "metric_methodology": {
            "pe": "Trailing reported earnings; only positive, in-range observations enter sector medians.",
            "pb": "Latest reported book equity available in the warehouse; not tangible book or average equity unless the source record explicitly says so. Interpret alongside ROE.",
            "ev_ebitda": "Provider-reported headline EV/EBITDA. EBITDA is not normalized; lease liabilities, minorities, investments and cash adjustments require reconciliation before a valuation conclusion.",
        },
        "interpretation": {
            "type": "agi_model_output",
            "warning": "Low or high median P/E is descriptive and is not, by itself, an attractiveness conclusion.",
        },
        "note": "Sector figures are reproducible equal-weighted medians across the covered universe.",
    }


def factor_dashboard(universe=None, medians=None) -> dict[str, Any]:
    """Universe-level factor readings: how much of each factor is available today."""
    rows = universe if universe is not None else _universe()
    if not rows:
        return {"ok": False, "error": "universe_empty"}

    def share(predicate) -> tuple[int, float]:
        hits = [r for r in rows if predicate(r)]
        return len(hits), round((len(hits) / len(rows)) * 100.0, 1)

    factors = []
    definitions = [
        ("Value", lambda r: (_sane(r, "pe") or 999) < 15, "P/E below 15"),
        ("Quality", lambda r: (_sane(r, "roe") or -999) > 18, "Return on equity above 18%"),
        ("Profitability", lambda r: (_sane(r, "profit_margin") or -999) > 15, "Net margin above 15%"),
        ("Momentum", lambda r: (_num((r.get("consensus") or {}).get("return_1y")) or -999) > 25,
         "One-year return above 25%"),
        ("Dividend", lambda r: (_sane(r, "dividend_yield") or -1) > 3, "Yield above 3%"),
        ("Leverage risk", lambda r: (_sane(r, "debt_to_equity") or -1) > 150, "Debt/equity above 150"),
    ]
    for name, predicate, definition in definitions:
        count, pct = share(predicate)
        factors.append({"factor": name, "companies": count, "share_pct": pct, "definition": definition})

    return {
        "ok": True,
        "universe": len(rows),
        "factors": factors,
        "methodology": {
            "period": universe_meta().get("as_of"),
            "universe": "covered warehouse universe",
            "basis": "latest available annual fundamentals and stored trailing market metrics",
            "exclusions": "missing values fail the relevant screen; financial companies are not yet separated",
            "source": "warehouse historical ratios, valuation and price history",
            "warning": "These are screening counts, not pure academic factor portfolios.",
        },
    }


# ---------------------------------------------------------------------------
# Explain a single opportunity
# ---------------------------------------------------------------------------
def opportunity(ticker: str, limit: int = 1000) -> dict[str, Any]:
    tk = str(ticker or "").strip().upper()
    if not tk:
        return {"ok": False, "error": "ticker_required"}

    run = run_all(limit=limit)
    if not run.get("ok"):
        return {"ok": False, "error": run.get("error") or "universe_empty"}
    universe, medians, results = run["universe"], run["medians"], run["results"]

    row = next((r for r in universe if str(r.get("ticker") or "").upper() == tk), None)
    if row is None:
        return {"ok": False, "error": "not_covered", "ticker": tk}

    industry = row.get("primary_industry")
    med = medians.get(industry) or {}
    consensus = row.get("consensus") or {}
    metric = _primary_metric(row.get("industry_dna"))
    value, benchmark = _sane(row, metric), _num(med.get(metric))
    roe, roe_med = _sane(row, "roe"), _num(med.get("roe"))
    margin = _sane(row, "profit_margin")
    debt = _sane(row, "debt_to_equity")
    yld = _sane(row, "dividend_yield")
    r1 = _num(consensus.get("return_1y"))

    matched = []
    for key in _ORDER:
        for hit in results[key]:
            if _identity(hit)[0] == tk:
                matched.append(
                    {
                        "strategy": key,
                        "label": SCANS[key][0],
                        "confidence": hit.get("confidence"),
                        "why": hit.get("why"),
                        "research_question": _SCAN_PROFILE.get(key, {}).get("question"),
                    }
                )
                break

    gap = round(((value / benchmark) - 1.0) * 100.0, 1) if value and benchmark else None

    chain = []
    if value is not None and benchmark:
        chain = [
            {"step": f"{metric.upper()} today", "value": value},
            {"step": f"{industry} median {metric.upper()}", "value": benchmark},
            {"step": "Gap to industry", "value": f"{gap}%"},
            {"step": "Return on equity", "value": f"{roe}%" if roe is not None else "—"},
            {"step": "Industry median return on equity", "value": f"{roe_med}%" if roe_med is not None else "—"},
            {"step": "Debt / equity", "value": debt if debt is not None else "—"},
            {"step": "Consensus upside", "value": f"{consensus.get('upside')}%" if consensus.get("upside") is not None else "—"},
        ]

    risks, catalysts = [], []
    if debt is not None and debt > 120:
        risks.append(f"Leverage: debt/equity at {debt}.")
    if margin is not None and margin < 5:
        risks.append(f"Thin profitability: net margin of {margin}%.")
    if gap is not None and gap < -25 and roe is not None and roe_med is not None and roe < roe_med:
        risks.append("The discount coincides with below-industry returns — a value trap until proven otherwise.")
    if r1 is not None and r1 < -15:
        risks.append(f"Price already down {abs(r1)}% over a year; the market is discounting something.")
    if not risks:
        risks.append("No leverage, margin or drawdown flag in the covered metrics — risk work still required on the business itself.")

    if consensus.get("upside") is not None:
        catalysts.append(f"Consensus target implies {consensus.get('upside')}% against the current price.")
    if gap is not None and gap < -20:
        catalysts.append("Re-rating toward the industry median if returns hold.")
    if roe is not None and roe_med is not None and roe > roe_med:
        catalysts.append("Above-industry returns on equity that the multiple has not yet reflected.")
    if not catalysts:
        catalysts.append("No mechanical catalyst in the covered data — a catalyst would have to come from results or corporate action.")

    # Timeline from the daily snapshots.
    timeline = []
    days = _load_snapshots().get("days") or {}
    prior_state: dict[str, bool] = {}
    for day in sorted(days):
        state = {key: tk in (days[day].get(key) or []) for key in _ORDER}
        for key, present in state.items():
            was = prior_state.get(key)
            if was is None and present:
                timeline.append({"date": day, "event": f"Entered {SCANS[key][0]} scanner"})
            elif was is False and present:
                timeline.append({"date": day, "event": f"Re-entered {SCANS[key][0]} scanner"})
            elif was is True and not present:
                timeline.append({"date": day, "event": f"Left {SCANS[key][0]} scanner"})
        prior_state = state

    bottom = (
        f"{row.get('company_name') or tk} is surfaced by {len(matched)} "
        f"{'scanner' if len(matched) == 1 else 'independent scanners'}"
        + (f" ({', '.join(m['label'] for m in matched)})" if matched else "")
        + ". That makes it a research priority, not a position — the scanners describe what the "
        "data looks like today, not what the business is worth."
    ) if matched else (
        f"{row.get('company_name') or tk} does not currently satisfy any scanner. It is covered, "
        "with metrics and consensus attached, but nothing in today's data flags it for research."
    )

    return {
        "ok": True,
        "ticker": tk,
        "company_name": row.get("company_name"),
        "sector": row.get("primary_sector"),
        "industry": industry,
        "identity_source": "warehouse.company_master",
        "market": {
            "price": row.get("price"),
            "market_cap": row.get("market_cap"),
            "pe": _sane(row, "pe"),
            "forward_pe": _sane(row, "forward_pe"),
            "pb": _sane(row, "pb"),
            "ev_ebitda": _sane(row, "ev_ebitda"),
            "dividend_yield": yld,
            "source": SOURCES["market_data"],
        },
        "quality": {
            "roe": roe,
            "profit_margin": margin,
            "debt_to_equity": debt,
            "source": SOURCES["fundamentals"],
        },
        "industry_context": {
            "primary_metric": metric,
            "company_value": value,
            "industry_median": benchmark,
            "gap_pct": gap,
            "industry_median_roe": roe_med,
            "peers": med.get("count"),
            "source": "agi_industry_intelligence",
        },
        "consensus": {
            "upside": consensus.get("upside"),
            "coverage": consensus.get("coverage"),
            "buy_count": consensus.get("buy_count"),
            "target": consensus.get("target_price") or consensus.get("target"),
            "return_1y": r1,
            "source": consensus.get("source") or SOURCES["consensus"],
        },
        "factors": row.get("factors") or {},
        "strategies_matched": matched,
        "calculation_chain": chain,
        "risks": risks,
        "catalysts": catalysts,
        "timeline": timeline[-20:],
        "bottom_line": bottom,
        "policy": "Descriptive research observation. No buy, sell, target price or personalised advice.",
    }


def scan(strategy: str, *, limit: int = 20, sector: Optional[str] = None) -> dict[str, Any]:
    """One scanner, with confidence attached and the full explanation per row."""
    key = str(strategy or "").strip().lower()
    if key in {"technical", "momentum"}:
        return {
            "ok": False,
            "error": "technical_research_paused",
            "message": "Technical and momentum scans are paused. Alpha currently uses fundamentals and earnings consensus only.",
            "available": _ORDER,
        }
    if key not in SCANS:
        return {"ok": False, "error": "unknown_scan", "available": _ORDER}

    rows = _universe()
    if sector:
        rows = [r for r in rows if str(r.get("primary_sector") or "").lower() == sector.lower()]
    if not rows:
        return {"ok": False, "error": "universe_empty"}

    medians = _industry_medians(rows)
    label, fn = SCANS[key]
    results = fn(rows, medians, max(1, min(60, int(limit or 20))))
    for row in results:
        row["confidence"] = _confidence(key, row)
    profile = _SCAN_PROFILE.get(key, {})
    return {
        "ok": True,
        "scan": key,
        "label": label,
        "alpha_source": profile.get("alpha"),
        "risk_level": profile.get("risk"),
        "research_question": profile.get("question"),
        "universe_scanned": len(rows),
        "results": results,
        "count": len(results),
        "sources": dict(SOURCES),
        "universe_meta": universe_meta(),
        "policy": "Research observations only — no buy, sell or price target.",
    }
