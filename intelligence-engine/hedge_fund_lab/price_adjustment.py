"""Corporate-action adjusted prices, built because the warehouse column is empty.

daily_market_history carries an `adjusted_close` column and it is unpopulated:
0 of 500 sampled rows on 2026-08-19. Raw `close` is unusable for return
measurement, because a 1:1 bonus halves the quoted price with no economic loss
and would register as a -50% month. Indian issuers use bonuses and splits
heavily, so this is not an edge case — it would corrupt every backtest run on
this data.

corporate_actions holds 25,468 rows with split, bonus, rights and dividend
fields, which is enough to build the adjustment here.

Method. Working backwards from the present, a price observed before an action
is restated onto today's share base by multiplying it by the cumulative factor
of every action that has happened since:

    adj(t) = close(t) * PROD over actions a with ex_date > t of f(a)

    split  1:n     f = 1/n     one old share becomes n
    bonus  m:n     f = n/(n+m) n shares become n+m
    rights          not adjusted - see below

Rights issues are deliberately excluded. Adjusting them correctly needs the
subscription price and take-up rate, neither of which is in the table, and a
wrong rights adjustment is worse than none because it silently shifts the whole
history. Rows affected by a rights issue are flagged instead.

This is also the evidence the validation registry asks for under
CORPORATE_ACTION_UNVERIFIED, which currently blocks the pairs strategy: an
unadjusted split is indistinguishable from a violent mean-reversion signal.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Iterable, Optional

# Ratios appear as "1:2", "1 : 2", "1-2" or bare numbers depending on source.
_RATIO = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[:\-/]\s*(\d+(?:\.\d+)?)\s*$")


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip()[:10], fmt).date()
            except ValueError:
                continue
    return None


def _ratio(value: Any) -> Optional[tuple[float, float]]:
    """Parse 'a:b' into (a, b). Returns None when unparseable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-", "0"}:
        return None
    m = _RATIO.match(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (a, b) if a > 0 and b > 0 else None
    # A bare number on a split field means "1 becomes n".
    try:
        n = float(text)
    except ValueError:
        return None
    return (1.0, n) if n > 0 else None


def split_factor(value: Any) -> Optional[float]:
    """A 1:n split multiplies share count by n, so prior prices scale by 1/n."""
    parsed = _ratio(value)
    if not parsed:
        return None
    old, new = parsed
    return old / new if new else None


def bonus_factor(value: Any) -> Optional[float]:
    """An m:n bonus gives m new shares per n held: n shares become n+m."""
    parsed = _ratio(value)
    if not parsed:
        return None
    m, n = parsed
    total = n + m
    return n / total if total else None


def action_factor(action: dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    """Price factor for one corporate action, and why it was skipped if it was."""
    kind = str(action.get("action_type") or "").strip().lower()
    if kind == "split" or action.get("split"):
        f = split_factor(action.get("split") or action.get("ratio"))
        return (f, None) if f else (None, "unparseable_split")
    if kind == "bonus" or action.get("bonus"):
        f = bonus_factor(action.get("bonus") or action.get("ratio"))
        return (f, None) if f else (None, "unparseable_bonus")
    if kind == "rights" or action.get("rights"):
        # Needs subscription price and take-up; a wrong adjustment silently
        # shifts the entire prior history, which is worse than none.
        return None, "rights_not_adjusted"
    if kind == "dividend" or action.get("dividend"):
        # Price-return series only. Total return would need the dividend
        # reinvested, which is a different question and should be labelled.
        return None, "dividend_price_return_only"
    return None, "unhandled_action_type"


def build_factors(actions: Iterable[dict[str, Any]]) -> dict[str, list[tuple[date, float]]]:
    """Per-symbol list of (ex_date, factor), newest first."""
    by_symbol: dict[str, list[tuple[date, float]]] = {}
    for action in actions or []:
        symbol = str(action.get("symbol") or "").strip().upper()
        when = _as_date(action.get("action_date") or action.get("ex_date"))
        if not symbol or not when:
            continue
        factor, _ = action_factor(action)
        if factor is None or factor <= 0 or factor == 1.0:
            continue
        by_symbol.setdefault(symbol, []).append((when, factor))
    for rows in by_symbol.values():
        rows.sort(key=lambda r: r[0], reverse=True)
    return by_symbol


def adjust_series(
    prices: list[tuple[date, float]],
    factors: list[tuple[date, float]],
) -> list[tuple[date, float]]:
    """Restate a price series onto the current share base.

    Each observation is multiplied by the cumulative factor of every action
    dated after it, so the most recent price is unchanged and history is
    scaled to match.
    """
    if not prices:
        return []
    ordered = sorted(prices, key=lambda p: p[0])
    out: list[tuple[date, float]] = []
    for when, price in ordered:
        cumulative = 1.0
        for ex_date, factor in factors or []:
            if ex_date > when:
                cumulative *= factor
        out.append((when, price * cumulative))
    return out


def monthly_returns(series: list[tuple[date, float]]) -> list[tuple[date, float]]:
    """Simple returns between consecutive adjusted observations."""
    ordered = sorted(series, key=lambda p: p[0])
    out: list[tuple[date, float]] = []
    for (_, prev), (when, curr) in zip(ordered, ordered[1:]):
        if prev and prev > 0:
            out.append((when, curr / prev - 1.0))
    return out


def audit(actions: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """What the adjustment could and could not handle.

    This is the receipt the validation registry wants under
    CORPORATE_ACTION_UNVERIFIED. An adjustment that silently drops what it
    cannot parse is exactly as dangerous as no adjustment at all.
    """
    counts: dict[str, int] = {}
    applied = 0
    symbols: set[str] = set()
    for action in actions or []:
        symbol = str(action.get("symbol") or "").strip().upper()
        if symbol:
            symbols.add(symbol)
        factor, reason = action_factor(action)
        if factor is not None:
            applied += 1
            counts["applied"] = counts.get("applied", 0) + 1
        else:
            counts[reason or "unknown"] = counts.get(reason or "unknown", 0) + 1
    return {
        "ok": True,
        "actions_seen": sum(counts.values()),
        "adjustments_applied": applied,
        "symbols": len(symbols),
        "breakdown": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "limitations": [
            "Rights issues are not adjusted: subscription price and take-up are absent.",
            "Dividends are not reinvested, so this is a price-return series.",
            "Adjustment is built here because warehouse adjusted_close is unpopulated.",
        ],
    }
