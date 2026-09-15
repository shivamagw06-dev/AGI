"""Notice that a company has reported, by asking Upstox what period it now has.

Deliberately the dullest possible signal. Not a move in PE, not narrative text,
not price behaviour - those correlate with results and are not results. PE moves
every day the market opens; a company reports four times a year.

So: what is the newest period Upstox holds, and is it newer than ours? If yes,
that company is owed a refresh. If no, nothing happened.

A newly observed period is not automatically a valid one. A vendor can return a
period dated in the future, a period older than the one it gave yesterday, or a
payload for a different company entirely. Each of those is rejected here rather
than queued, because a queue that faithfully processes nonsense is worse than
one that never heard about it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterable, Optional

# Period parsing lives in the warehouse: the same four spellings have to resolve
# identically for a detector deciding what is new and for a gateway deciding
# which rows are one period. Two copies would drift apart.
from institutional_warehouse.period_identity import parse_period
from valuation_ratios.sweep import USER_AGENT, _token, safe_pause

BASE = "https://api.upstox.com/v2/fundamentals"

# A period more than a quarter into the future is not a reporting period; it is
# a parsing error or a vendor bug. Results are published after the period ends.
FUTURE_TOLERANCE_DAYS = 95

# Nothing before this is a plausible modern reporting period for this universe.
EARLIEST_PLAUSIBLE = date(1995, 1, 1)

def validate_period(candidate: Any, *, held: Any = None,
                    today: Optional[date] = None) -> tuple[bool, str]:
    """Whether a newly seen period is worth queueing.

    Rejections, each for something a vendor has actually been known to do:
    a period that will not parse; one dated into the future; one older than what
    we already hold, which means the feed went backwards rather than forwards.
    """
    when = parse_period(candidate)
    if when is None:
        return False, "unparseable_period"
    anchor = today or datetime.now(timezone.utc).date()
    if (when - anchor).days > FUTURE_TOLERANCE_DAYS:
        return False, "period_in_the_future"
    if when < EARLIEST_PLAUSIBLE:
        return False, "period_implausibly_old"
    prior = parse_period(held)
    if prior and when < prior:
        return False, "period_moved_backwards"
    if prior and when == prior:
        return False, "period_unchanged"
    return True, "new_period"


def latest_upstox_period(isin: str, *, timeout: float = 20.0) -> dict[str, Any]:
    """The newest annual period Upstox reports for a company."""
    token = _token()
    if not token:
        return {"ok": False, "error": "no_upstox_token"}
    request = urllib.request.Request(
        f"{BASE}/{isin}/income-statement?time_period=quarterly",
        headers={"Accept": "application/json", "Api-Version": "2.0",
                 "User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            body = ""
        return {"ok": False, "error": f"http_{exc.code}", "detail": body}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}
    return {"ok": True, "period": newest_period_in(payload), "payload": payload}


def newest_period_in(payload: Any) -> Optional[str]:
    """The latest period label anywhere in an income-statement response.

    Read structurally rather than by position: Upstox groups history under
    revenue, operating_profit and net_profit, and the order within each is not
    something to rely on.
    """
    seen: list[tuple[date, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            label = node.get("period")
            when = parse_period(label)
            if when:
                seen.append((when, str(label)))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return max(seen)[1] if seen else None


def held_period(symbol: str, *, tab: str = "financials_quarterly") -> Optional[str]:
    """The newest period AGI already holds for a company."""
    from institutional_warehouse import store

    rows = store.fetch(tab, filters={"symbol": str(symbol).strip().upper()},
                       limit=200).get("rows") or []
    field = "fiscal_period" if tab == "financials_quarterly" else "fiscal_year"
    labels = [str(r.get(field) or "") for r in rows if r.get(field)]
    dated = [(parse_period(l), l) for l in labels]
    dated = [d for d in dated if d[0]]
    return max(dated)[1] if dated else None


def detect(companies: Iterable[dict[str, Any]], *,
           fetch: Optional[Callable[[str], dict[str, Any]]] = None,
           pause_seconds: Optional[float] = None,
           today: Optional[date] = None,
           force: bool = False) -> dict[str, Any]:
    """Ask each company whether it has reported since we last looked."""
    import time

    from fundamentals_refresh import queue as q

    fetch = fetch or (lambda isin: latest_upstox_period(isin))
    pause = safe_pause(pause_seconds)

    found: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    unchanged = failed = 0

    for company in companies or []:
        symbol = str(company.get("symbol") or "").strip().upper()
        isin = str(company.get("isin") or "").strip()
        if not symbol or not isin:
            continue
        result = fetch(isin)
        if not result.get("ok"):
            failed += 1
        else:
            candidate = result.get("period")
            mine = company.get("held_period", ...)
            mine = held_period(symbol) if mine is ... else mine
            ok, reason = validate_period(candidate, held=mine, today=today)
            if force and not ok and reason == "period_unchanged":
                # A deliberate recollection of a period we already hold.
                ok = True
            if ok:
                found.append({"symbol": symbol, "reporting_period": str(candidate),
                              "trigger": q.TRIGGER_NEW_PERIOD})
            elif reason == "period_unchanged":
                unchanged += 1
            else:
                rejected.append({"symbol": symbol, "period": candidate, "reason": reason})
        if pause:
            time.sleep(pause)

    queued = q.enqueue(found, force=force) if found else {"queued": 0, "skipped": 0}
    return {
        "ok": True,
        "checked": len(list(companies)) if isinstance(companies, list) else None,
        "new_periods": len(found),
        "unchanged": unchanged,
        "rejected": len(rejected),
        "failed": failed,
        "queued": queued.get("queued", 0),
        "already_queued": queued.get("skipped", 0),
        "rejections": rejected[:25],
        "sample": found[:25],
    }
