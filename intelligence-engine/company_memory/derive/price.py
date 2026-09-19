"""Price Intelligence — returns, drawdowns, volatility (derived, not raw OHLCV dump)."""

from __future__ import annotations

import math
from typing import Any


def _closes_from_hd(entity: str) -> list[tuple[str, float]]:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        series = hd_store.get_series("prices", entity) or {}
        out: list[tuple[str, float]] = []
        for r in series.get("records") or []:
            px = (r.get("payload") or {}).get("adj_close")
            pe = r.get("period_end") or r.get("period")
            if px is not None and pe:
                out.append((str(pe)[:10], float(px)))
        return out
    except Exception:
        return []


def _yahoo_monthly(entity: str) -> list[tuple[str, float]]:
    try:
        import json
        import urllib.request
        from datetime import datetime, timezone

        try:
            from app.market_data.providers.yahoo_symbols import to_yahoo_symbol

            sym = to_yahoo_symbol(entity)
        except Exception:
            sym = f"{entity.upper()}.NS"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1mo&range=10y"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AGIB-CompanyMemory/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return []
        ts = result[0].get("timestamp") or []
        closes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
        out: list[tuple[str, float]] = []
        for t, c in zip(ts, closes):
            if c is None:
                continue
            dt = datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat()
            out.append((dt, float(c)))
        return out
    except Exception:
        return []


def _return_pct(closes: list[float], months: int) -> float | None:
    if len(closes) < months + 1:
        if len(closes) < 2:
            return None
        a, b = closes[0], closes[-1]
    else:
        a, b = closes[-(months + 1)], closes[-1]
    if a <= 0:
        return None
    return round((b / a - 1.0) * 100.0, 2)


def _max_drawdown(closes: list[float], dates: list[str]) -> dict[str, Any]:
    if not closes:
        return {}
    peak = closes[0]
    peak_i = 0
    max_dd = 0.0
    trough_i = 0
    start_i = 0
    for i, c in enumerate(closes):
        if c > peak:
            peak = c
            peak_i = i
        dd = c / peak - 1.0 if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
            trough_i = i
            start_i = peak_i
    # Recovery: first date after trough back to peak level
    recovery = None
    peak_level = closes[start_i]
    for j in range(trough_i + 1, len(closes)):
        if closes[j] >= peak_level:
            recovery = dates[j]
            break
    return {
        "max_drawdown_pct": round(max_dd * 100.0, 2),
        "peak_date": dates[start_i] if dates else None,
        "trough_date": dates[trough_i] if dates else None,
        "recovery_date": recovery,
        "recovered": recovery is not None,
    }


def derive_price_intelligence(entity: str, *, allow_live: bool = True) -> dict[str, Any]:
    pairs = _closes_from_hd(entity)
    source = "historical_depth.prices"
    if len(pairs) < 12 and allow_live:
        y = _yahoo_monthly(entity)
        if len(y) > len(pairs):
            pairs = y
            source = "yahoo_chart_monthly"
    if len(pairs) < 2:
        return {
            "available": False,
            "entity": entity,
            "source": source,
            "reason": "insufficient_price_history",
        }
    dates = [p[0] for p in pairs]
    closes = [p[1] for p in pairs]
    rets = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            rets.append((closes[i] / closes[i - 1] - 1.0) * 100.0)
    vol = None
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        vol = round(math.sqrt(sum((x - mean) ** 2 for x in rets) / len(rets)), 4)

    # Soft HD risk producer overlay
    risk = {}
    try:
        from knowledge_factory.historical_depth.producers.derived import produce_risk_momentum

        risk = produce_risk_momentum(entity) or {}
    except Exception:
        risk = {}

    dd = _max_drawdown(closes, dates)
    return {
        "available": True,
        "entity": entity,
        "source": source,
        "observations": len(closes),
        "history_start": dates[0],
        "history_end": dates[-1],
        "latest_price": closes[-1],
        "return_1y_pct": _return_pct(closes, 12),
        "return_3y_pct": _return_pct(closes, 36),
        "return_5y_pct": _return_pct(closes, 60),
        "return_10y_pct": _return_pct(closes, 120),
        "monthly_volatility_pct": vol if vol is not None else risk.get("monthly_vol_pct"),
        "momentum_12m_pct": risk.get("momentum_12m_pct"),
        "drawdown": dd,
        "beta_vs_nifty": None,  # requires index series — reserved
        "relative_vs_nifty": None,
        "relative_vs_sector": None,
        "cycle_notes": [],
        "lineage": [{"source": source, "n": len(closes)}],
    }
