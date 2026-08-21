"""The daily sweep of Upstox key ratios across the universe.

The warehouse already holds these snapshots and has the right shape for them -
append-only, keyed by company, ratio and date. What it did not have was anything
that swept. Ingest was push-based: something outside the engine fetched a
company and posted it in, so the table recorded whoever happened to be looked at.
Coverage ran at twenty-five to eighty companies a day out of 2,431.

This pulls instead. It is the piece that turns a vendor's point-in-time values
into a history we own: Upstox's Key Ratios endpoint carries no time dimension at
all, so every day it is not collected is a day that cannot be recovered later.

The rules it works to, all learned from something that went wrong here:

* One bad company never fails the run. A batch that aborts on the first bad
  payload loses the twenty-four healthy companies behind it.
* A failed call writes nothing. A null is not a reading, and writing one turns
  a good figure on the desk into a blank with no explanation.
* Rows are validated and batched before they are promoted, so a malformed
  response is quarantined rather than published.
* Coverage decides whether the run is honest. A sweep that reached 40% of the
  universe is not a complete daily snapshot and must not be reported as one.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional

SOURCE = "upstox"
KIND = "upstox_key_ratios"
BASE = "https://api.upstox.com/v2/fundamentals"

# Shared with the candle collector, which met the same Cloudflare rule first.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Standard APIs allow 2,000 requests per 30 minutes. One a second leaves plenty
# of headroom and keeps the engine's own database usable while the sweep runs.
PAUSE_SECONDS = 0.6

# How much of the eligible universe a run must reach before it counts as a
# complete daily snapshot rather than a partial one.
HEALTHY_COVERAGE_PCT = 95.0
DEGRADED = "DEGRADED"
HEALTHY = "HEALTHY"
FAILED = "FAILED"

# The six the endpoint actually returns. Anything else in the payload is not a
# key ratio and is not promoted.
EXPECTED = ("pe", "pb", "roa", "roe", "roce", "ev_ebitda")


def _token() -> str:
    return (os.getenv("UPSTOX_ACCESS_TOKEN") or "").strip()


def eligible(limit: Optional[int] = None) -> list[dict[str, Any]]:
    """Companies Upstox can be asked about at all.

    Fundamentals are addressed by ISIN, so a company without one cannot be
    fetched. Those are skipped with a reason rather than counted as failures -
    283 of them is a mapping gap, not 283 broken API calls.
    """
    from institutional_warehouse import store

    out: list[dict[str, Any]] = []
    for row in store.all_rows("company_master", limit=20000) or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        isin = str(row.get("isin") or "").strip().upper()
        if not symbol:
            continue
        out.append({"symbol": symbol, "isin": isin,
                    "company_id": str(row.get("company_id") or symbol),
                    "instrument_key": row.get("instrument_key")})
    out.sort(key=lambda r: r["symbol"])
    return out[:limit] if limit else out


def fetch_ratios(isin: str, *, timeout: float = 20.0) -> dict[str, Any]:
    """One company's key ratios, or a reason it could not be had."""
    token = _token()
    if not token:
        return {"ok": False, "error": "no_upstox_token"}
    # The default urllib user agent is refused by Upstox's Cloudflare with
    # error 1010 - a blocked client fingerprint, not an auth failure. The candle
    # collector hit this first and carries the same header for the same reason.
    request = urllib.request.Request(
        f"{BASE}/{isin}/key-ratios",
        headers={"Accept": "application/json",
                 "Api-Version": "2.0",
                 "User-Agent": USER_AGENT,
                 "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"ok": True, "payload": json.loads(response.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        # The status alone does not say whether the token expired, the plan does
        # not cover this endpoint, or the ISIN is unknown - and Upstox access
        # tokens expire daily, so 403 is the expected shape of a stale one.
        try:
            body = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            body = ""
        return {"ok": False, "error": f"http_{exc.code}", "detail": body}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def _rows_for(company: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    from valuation_ratios.ingest import normalise_upstox_key_ratios

    body = payload.get("data") if isinstance(payload, dict) else None
    return normalise_upstox_key_ratios({
        "symbol": company["symbol"], "isin": company["isin"],
        "company_id": company.get("company_id"),
        "instrument_key": company.get("instrument_key"),
        "data": body if body is not None else payload,
    })


def completeness(rows: Iterable[dict[str, Any]]) -> tuple[int, list[str]]:
    """How many of the six arrived, and which did not.

    A response carrying five of six is not a complete snapshot. It is promoted
    with what it has and recorded as incomplete, because pretending otherwise
    makes a gap look like a value nobody has questioned.
    """
    have = {str(r.get("ratio_name") or "") for r in rows or []}
    missing = [r for r in EXPECTED if r not in have]
    return len(EXPECTED) - len(missing), missing


def run(*, limit: Optional[int] = None, batch_size: int = 40, actor: str = "ratio_sweep",
        fetch: Optional[Callable[[str], dict[str, Any]]] = None,
        pause_seconds: float = PAUSE_SECONDS) -> dict[str, Any]:
    """Sweep the universe once and record honestly how far it got."""
    from institutional_warehouse import gateway
    from institutional_warehouse.backfill import checkpoints

    fetch = fetch or (lambda isin: fetch_ratios(isin))
    universe = eligible(limit)
    run_id = checkpoints.start_job(KIND, actor=actor,
                                   params={"limit": limit, "batch_size": batch_size})
    started = datetime.now(timezone.utc)

    requested = successful = failed = invalid = skipped = 0
    incomplete: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    staged: list[dict[str, Any]] = []
    written = {"inserted": 0, "updated": 0, "unchanged": 0, "quarantined": 0}

    def promote() -> None:
        """Batched on purpose: one commit per company is 2,431 write locks."""
        nonlocal staged
        if not staged:
            return
        out = gateway.write("valuation_ratios", staged, source=SOURCE, actor=actor,
                            reason=f"daily_key_ratios:{run_id}")
        for key in written:
            written[key] += int(out.get(key) or 0)
        staged = []

    eligible_count = 0
    for company in universe:
        if not company["isin"]:
            # A mapping gap, not a broken call. Counted apart so coverage is
            # measured against what could actually be fetched.
            skipped += 1
            continue
        eligible_count += 1
        requested += 1
        result = fetch(company["isin"])
        if not result.get("ok"):
            failed += 1
            failures.append({"symbol": company["symbol"], "error": result.get("error"),
                             "detail": result.get("detail")})
        else:
            rows = _rows_for(company, result.get("payload") or {})
            if not rows:
                # A response we could not read is quarantined by absence rather
                # than promoted as a company with no ratios.
                invalid += 1
                failures.append({"symbol": company["symbol"], "error": "no_usable_ratios"})
            else:
                found, missing = completeness(rows)
                if missing:
                    incomplete.append({"symbol": company["symbol"], "have": found,
                                       "missing": missing})
                staged.extend(rows)
                successful += 1
        if len(staged) >= batch_size * len(EXPECTED):
            promote()
        if pause_seconds:
            time.sleep(pause_seconds)
    promote()

    coverage = round(100.0 * successful / eligible_count, 2) if eligible_count else 0.0
    status = (FAILED if not successful
              else HEALTHY if coverage >= HEALTHY_COVERAGE_PCT
              else DEGRADED)
    stats = {
        "eligible": eligible_count, "requested": requested, "successful": successful,
        "failed": failed, "invalid": invalid, "skipped_no_isin": skipped,
        "incomplete": len(incomplete), "coverage_pct": coverage, "status": status,
        "written": written,
        "seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 1),
    }
    checkpoints.finish_job(run_id, ok=status == HEALTHY, stats=stats)
    return {"ok": status != FAILED, "run_id": run_id, **stats,
            "failures": failures[:25], "incomplete_sample": incomplete[:25],
            "note": ("coverage below 95% is reported DEGRADED rather than as a "
                     "complete daily snapshot")}
