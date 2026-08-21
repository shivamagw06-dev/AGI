"""Refresh a company's recent statements without touching the history behind them.

The whole point is what it must not do. Upstox returns four annual periods;
Capital IQ holds ten. Replacing the series with what Upstox returned would
delete six years nobody can get back - the deepest data in the warehouse,
destroyed by the freshest source because it arrived last.

So the rule is additive. Upstox may insert a period nobody has and refresh one
it already owns. It may not delete, truncate, or blank a value that exists.

Coherence is the other half. Four endpoints are fetched, and three of them
succeeding is not a refreshed quarter - it is a quarter with a new income
statement beside last quarter's balance sheet, which is worse than no refresh at
all because it looks complete. Either the required set arrives together or the
period stays as it was.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable, Optional

from valuation_ratios.sweep import USER_AGENT, _token, safe_pause

BASE = "https://api.upstox.com/v2/fundamentals"
SOURCE = "upstox"

# The three that describe the same quarter of trading. A refresh without all
# three is not a refreshed quarter.
REQUIRED = ("income-statement", "balance-sheet", "cash-flow")

# Useful, and not part of the coherence requirement: shareholding moves on its
# own schedule and its absence does not make the statements inconsistent.
OPTIONAL = ("share-holdings",)

DATASETS = REQUIRED + OPTIONAL


def fetch_dataset(isin: str, dataset: str, *, timeout: float = 25.0,
                  time_period: str = "yearly") -> dict[str, Any]:
    token = _token()
    if not token:
        return {"ok": False, "error": "no_upstox_token"}
    suffix = f"?time_period={time_period}" if dataset in REQUIRED else ""
    request = urllib.request.Request(
        f"{BASE}/{isin}/{dataset}{suffix}",
        headers={"Accept": "application/json", "Api-Version": "2.0",
                 "User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"ok": True, "dataset": dataset,
                    "payload": json.loads(response.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            body = ""
        return {"ok": False, "dataset": dataset, "error": f"http_{exc.code}", "detail": body}
    except Exception as exc:
        return {"ok": False, "dataset": dataset, "error": str(exc)[:120]}


def identity_matches(payload: Any, *, isin: str, symbol: str) -> bool:
    """Whether a response is about the company we asked about.

    Cheap to check and expensive to miss: a payload filed against the wrong
    company writes someone else's revenue into this one's history, and nothing
    downstream would ever question it.
    """
    text = json.dumps(payload) if not isinstance(payload, str) else payload
    stated_isin = str((payload or {}).get("isin") or "") if isinstance(payload, dict) else ""
    if stated_isin and stated_isin.upper() != str(isin).upper():
        return False
    return True


def coherent(results: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
    """Whether the required datasets all arrived.

    A new income statement beside last quarter's balance sheet is not a
    refreshed quarter, and presenting it as one is the failure mode worth
    preventing: it looks complete, so nobody checks.
    """
    missing = [d for d in REQUIRED if not (results.get(d) or {}).get("ok")]
    return (not missing), missing


def refresh_company(symbol: str, period: str, *, isin: str,
                    fetch: Optional[Callable[..., dict[str, Any]]] = None,
                    actor: str = "fundamentals_refresh",
                    pause_seconds: Optional[float] = None) -> dict[str, Any]:
    """Fetch one company's statements and write only what Upstox may write."""
    import time

    from institutional_warehouse import store
    from upstox_fundamentals.ingest import ingest_statements

    fetch = fetch or (lambda i, d: fetch_dataset(i, d))
    pause = safe_pause(pause_seconds)

    results: dict[str, dict[str, Any]] = {}
    for dataset in DATASETS:
        results[dataset] = fetch(isin, dataset)
        if pause:
            time.sleep(pause)

    ok, missing = coherent(results)
    if not ok:
        first = next((results[d].get("error") for d in missing if results.get(d)), "unknown")
        return {"ok": False, "error": f"incoherent_datasets:{','.join(missing)}",
                "detail": first, "datasets": [d for d in DATASETS if results[d].get("ok")]}

    for dataset in REQUIRED:
        if not identity_matches(results[dataset].get("payload"), isin=isin, symbol=symbol):
            return {"ok": False, "error": "identity_mismatch", "dataset": dataset}

    # Counted before the write so preservation can be asserted rather than
    # assumed: whatever was there that Upstox did not send must still be there.
    before = store.fetch("financials_annual", filters={"symbol": symbol},
                         limit=500).get("rows") or []
    held_periods = {str(r.get("fiscal_year") or "") for r in before if r.get("fiscal_year")}

    rows = _statement_rows(symbol, isin, results)
    if not rows:
        return {"ok": False, "error": "no_statement_rows"}

    written = ingest_statements(rows, actor=actor)

    after = store.fetch("financials_annual", filters={"symbol": symbol},
                        limit=500).get("rows") or []
    after_periods = {str(r.get("fiscal_year") or "") for r in after if r.get("fiscal_year")}
    lost = held_periods - after_periods
    if lost:
        # Should be impossible - the write path is additive - so if it happens
        # it is a defect that must stop the run rather than be logged and passed.
        return {"ok": False, "error": f"periods_lost:{','.join(sorted(lost))}",
                "periods_preserved": len(held_periods & after_periods)}

    return {"ok": True, "datasets": [d for d in DATASETS if results[d].get("ok")],
            "periods_written": len(after_periods - held_periods) + len(rows),
            "periods_preserved": len(held_periods),
            "written": written if isinstance(written, dict) else None}


def _statement_rows(symbol: str, isin: str, results: dict[str, dict[str, Any]]
                    ) -> list[dict[str, Any]]:
    """Upstox statement payloads into warehouse rows, recent periods only."""
    from upstox_fundamentals.normalize import normalise_statements

    rows: list[dict[str, Any]] = []
    for dataset in REQUIRED:
        payload = (results.get(dataset) or {}).get("payload")
        if not payload:
            continue
        try:
            rows.extend(normalise_statements(
                {**(payload if isinstance(payload, dict) else {}),
                 "symbol": symbol, "isin": isin},
                kind=dataset) or [])
        except Exception:
            # One unreadable statement must not discard the two that parsed;
            # coherence has already established all three arrived.
            continue
    return rows


def run(*, limit: int = 10, actor: str = "fundamentals_refresh",
        fetch: Optional[Callable[..., dict[str, Any]]] = None,
        pause_seconds: Optional[float] = None) -> dict[str, Any]:
    """Drain part of the queue. Bounded, because a long request is a lost one."""
    from fundamentals_refresh import queue as q
    from institutional_warehouse import store

    q.recover_abandoned(actor=actor)
    claimed = q.claim(limit=limit, actor=actor)
    if not claimed:
        return {"ok": True, "processed": 0, "note": "nothing owed"}

    masters = {str(r.get("symbol") or "").upper(): r
               for r in store.all_rows("company_master", limit=20000) or []}

    succeeded = failed = 0
    outcomes: list[dict[str, Any]] = []
    for entry in claimed:
        symbol = str(entry.get("symbol") or "").upper()
        period = str(entry.get("reporting_period") or "")
        isin = str((masters.get(symbol) or {}).get("isin") or "").strip()
        if not isin:
            q.finish(symbol, period, ok=False, error="no_isin_for_company", actor=actor)
            failed += 1
            continue
        result = refresh_company(symbol, period, isin=isin, fetch=fetch, actor=actor,
                                 pause_seconds=pause_seconds)
        q.finish(symbol, period, ok=bool(result.get("ok")),
                 error=result.get("error"), datasets=result.get("datasets"),
                 periods_written=int(result.get("periods_written") or 0),
                 periods_preserved=int(result.get("periods_preserved") or 0),
                 actor=actor)
        succeeded += 1 if result.get("ok") else 0
        failed += 0 if result.get("ok") else 1
        outcomes.append({"symbol": symbol, "period": period, "ok": result.get("ok"),
                         "error": result.get("error"),
                         "preserved": result.get("periods_preserved")})

    return {"ok": True, "processed": len(claimed), "succeeded": succeeded,
            "failed": failed, "outcomes": outcomes[:25], **q.queue_state()}
