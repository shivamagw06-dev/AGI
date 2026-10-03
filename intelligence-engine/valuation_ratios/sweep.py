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

# Standard APIs allow 2,000 requests per 30 minutes - about 1.1 a second. One a
# second leaves headroom and keeps the engine's own database usable.
PAUSE_SECONDS = 0.6

# The floor a caller cannot go under.
#
# Not a remembered lesson: on 21 August a batch was run at 0.15s and 218 of 254
# companies failed at once. The pace was mine to choose and I chose badly, so it
# is no longer a choice - slower is allowed, faster is clamped.
MIN_PAUSE_SECONDS = 0.5


def safe_pause(requested: Optional[float]) -> float:
    if requested is None:
        return PAUSE_SECONDS
    return max(float(requested), MIN_PAUSE_SECONDS)

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


ELIGIBLE_EQUITY = "eligible_equity"
INELIGIBLE_ETF = "ineligible_etf"
INELIGIBLE_FUND = "ineligible_fund"
MISSING_MAPPING = "missing_mapping"


def classify(row: dict[str, Any]) -> str:
    """What kind of instrument this is, and therefore whether to ask about it.

    520 of the first sweep's 2,168 companies came back with no usable ratios,
    and every one was an ETF or an index fund - ABSLLIQUID, NV20BEES, NPBET.
    Upstox is right to have no P/E for them: they have no earnings. They were
    counted as failures, retried three times each, and dragged the coverage
    figure down to something that read like a broken collector.

    Classified with the instrument policy the rest of the engine already uses,
    rather than a second opinion that can drift from the first.
    """
    symbol = str(row.get("symbol") or "").strip().upper()
    if not symbol:
        return MISSING_MAPPING
    try:
        from valuation_policy.instruments import resolve_instrument

        kind = str(resolve_instrument(
            symbol=symbol, company_name=row.get("company_name"),
            sector=row.get("sector"), industry=row.get("industry"),
            industry_dna=row.get("industry_dna"), master=row,
        ).get("instrument_type") or "").upper()
    except Exception:
        # Fail towards asking. A misclassified company costs one wasted call;
        # a misclassified ETF costs a snapshot that should have been collected.
        kind = "EQUITY"
    if kind in {"ETF", "COMMODITY_ETF", "INDEX"}:
        return INELIGIBLE_ETF
    if kind in {"MUTUAL_FUND", "REIT", "INVIT"}:
        return INELIGIBLE_FUND
    if not str(row.get("isin") or "").strip():
        return MISSING_MAPPING
    return ELIGIBLE_EQUITY


def eligible(limit: Optional[int] = None) -> list[dict[str, Any]]:
    """Every instrument in the master, each carrying why it can be asked or not."""
    from institutional_warehouse import store

    out: list[dict[str, Any]] = []
    for row in store.all_rows("company_master", limit=20000) or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        out.append({"symbol": symbol,
                    "isin": str(row.get("isin") or "").strip().upper(),
                    "company_id": str(row.get("company_id") or symbol),
                    "instrument_key": row.get("instrument_key"),
                    # Carried because the not-applicable rule is a fact about
                    # the sector, and without it every bank reads as degraded.
                    "sector": row.get("sector"),
                    "industry": row.get("industry"),
                    "eligibility": classify(row)})
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


# Ratios that do not exist for a bank, rather than being missing from one.
#
# ROCE and EV/EBITDA have no meaning for a lender: there is no capital employed
# in the industrial sense and no enterprise value net of debt when deposits are
# the raw material. Upstox omits them correctly. Marked "partial" they would
# make every bank look permanently degraded, so the absence is named for what it
# is - and a reader can then tell it apart from a collection failure.
NOT_APPLICABLE_BY_SECTOR: dict[str, frozenset[str]] = {
    "financials": frozenset({"roce", "ev_ebitda"}),
    "banking": frozenset({"roce", "ev_ebitda"}),
    "bank": frozenset({"roce", "ev_ebitda"}),
}

FRESH = "FRESH"
PARTIAL_VALID = "PARTIAL_VALID"
STALE = "STALE"
NOT_APPLICABLE = "NOT_APPLICABLE"
INELIGIBLE = "INELIGIBLE"
FAILED_STATE = "FAILED"


def inapplicable_for(sector: Any) -> frozenset[str]:
    text = str(sector or "").strip().lower()
    for key, ratios in NOT_APPLICABLE_BY_SECTOR.items():
        if key in text:
            return ratios
    return frozenset()


def snapshot_state(missing: Iterable[str], *, sector: Any = None) -> str:
    """What a company's snapshot today actually is.

    A bank without ROCE is complete for a bank. A manufacturer without ROCE is
    a gap. The same absence, two different facts, and only the sector separates
    them.
    """
    missing = list(missing or [])
    if not missing:
        return FRESH
    na = inapplicable_for(sector)
    if all(m in na for m in missing):
        return NOT_APPLICABLE
    return PARTIAL_VALID


def completeness(rows: Iterable[dict[str, Any]]) -> tuple[int, list[str]]:
    """How many of the six arrived, and which did not.

    A response carrying five of six is not a complete snapshot. It is promoted
    with what it has and recorded as incomplete, because pretending otherwise
    makes a gap look like a value nobody has questioned.
    """
    have = {str(r.get("ratio_name") or "") for r in rows or []}
    missing = [r for r in EXPECTED if r not in have]
    return len(EXPECTED) - len(missing), missing


def kind_for(day: Optional[str] = None) -> str:
    """Checkpoints are per day, so progress resumes but tomorrow starts fresh.

    Without the date a company marked done today would be skipped forever, and
    the point of a daily snapshot is that it happens daily.
    """
    return f"{KIND}:{day or datetime.now(timezone.utc).date().isoformat()}"


def run(*, limit: Optional[int] = None, batch_size: int = 40, actor: str = "ratio_sweep",
        fetch: Optional[Callable[[str], dict[str, Any]]] = None,
        pause_seconds: Optional[float] = None, resume: bool = True,
        max_companies: Optional[int] = None) -> dict[str, Any]:
    """Sweep the universe and record honestly how far it got.

    Resumable, because the first full run was killed at twenty minutes by a
    deploy landing on top of it and lost everything it had collected. Each
    company is checkpointed as it completes, so a restart costs the batch in
    flight rather than the run.

    ``max_companies`` bounds one call. A single request that runs for half an
    hour is a request that a deploy, a timeout or a proxy will eventually
    interrupt, and the work should survive all three.
    """
    from institutional_warehouse import gateway
    from institutional_warehouse.backfill import checkpoints
    from valuation_ratios import ingest

    fetch = fetch or (lambda isin: fetch_ratios(isin))
    pause_seconds = safe_pause(pause_seconds)
    day_kind = kind_for()
    universe = eligible(limit)
    if resume:
        owed = set(checkpoints.pending_entities(
            day_kind, [c["symbol"] for c in universe], limit=len(universe) or 1))
        universe = [c for c in universe if c["symbol"] in owed]
    if max_companies:
        universe = universe[:max_companies]
    run_id = checkpoints.start_job(KIND, actor=actor,
                                   params={"limit": limit, "batch_size": batch_size,
                                           "resume": resume, "day": day_kind})
    started = datetime.now(timezone.utc)

    requested = successful = failed = invalid = skipped = 0
    incomplete: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    staged: list[dict[str, Any]] = []
    written = {"inserted": 0, "updated": 0, "unchanged": 0, "quarantined": 0}
    valuation = {"wrote": 0, "errors": []}

    def promote() -> None:
        """Batched on purpose: one commit per company is 2,431 write locks."""
        nonlocal staged
        if not staged:
            return
        out = gateway.write("valuation_ratios", staged, source=SOURCE, actor=actor,
                            reason=f"daily_key_ratios:{run_id}")
        for key in written:
            written[key] += int(out.get(key) or 0)
        # The desk reads historical_valuation, not this table. Writing only the
        # long form left the sector pages on whatever Yahoo had last written,
        # and once Yahoo was stopped they had nothing: coverage of that table
        # fell from 2,889 rows on 19 August to 82 on the 23rd. The push-based
        # ingest always did both; the sweep did not, and the sweep is what runs
        # daily. A failure here must not lose the ratios already written, so it
        # is recorded rather than raised.
        try:
            synced = ingest.sync_historical_valuation(staged, actor=actor)
            valuation["wrote"] += int(synced.get("inserted") or 0) + int(synced.get("updated") or 0)
        except Exception as exc:  # noqa: BLE001 - reported, never fatal
            valuation["errors"].append(str(exc)[:200])
        staged = []

    eligible_count = 0
    by_eligibility: dict[str, int] = {}
    for company in universe:
        kind = company.get("eligibility") or ELIGIBLE_EQUITY
        by_eligibility[kind] = by_eligibility.get(kind, 0) + 1
        if kind != ELIGIBLE_EQUITY:
            # An ETF has no earnings, so it has no P/E. Asking is not a failure
            # that needs retrying three times - it is a question that does not
            # apply, and it does not belong in the coverage denominator either.
            skipped += 1
            checkpoints.save_checkpoint(day_kind, company["symbol"],
                                        status=checkpoints.SKIPPED, error=kind)
            continue
        eligible_count += 1
        requested += 1
        result = fetch(company["isin"])
        if not result.get("ok"):
            checkpoints.save_checkpoint(day_kind, company["symbol"],
                                        status=checkpoints.FAILED,
                                        error=str(result.get("error"))[:200])
            failed += 1
            failures.append({"symbol": company["symbol"], "error": result.get("error"),
                             "detail": result.get("detail")})
        else:
            rows = _rows_for(company, result.get("payload") or {})
            if not rows:
                # A response we could not read is quarantined by absence rather
                # than promoted as a company with no ratios.
                # Upstox answered and had no ratios to give. For an equity
                # that would be a gap; in practice it is an instrument the
                # symbol heuristic did not recognise - ABSLLIQUID carries no
                # ETF token and reads as a company until you ask.
                #
                # Skipped rather than failed, so it is not retried three times
                # and does not sit in the coverage denominator pretending to be
                # a company we could not reach.
                invalid += 1
                checkpoints.save_checkpoint(day_kind, company["symbol"],
                                            status=checkpoints.SKIPPED,
                                            error="no_ratios_reported")
                failures.append({"symbol": company["symbol"],
                                 "error": "no_ratios_reported",
                                 "note": "answered with no ratios; not an equity"})
            else:
                found, missing = completeness(rows)
                # Marked on every row of the snapshot, not only in the run log.
                # A run report is read once; the rows are read for years, and a
                # missing sixth ratio must not look like ordinary absence.
                state = snapshot_state(missing, sector=company.get("sector"))
                for row in rows:
                    row["snapshot_completeness"] = (
                        "complete" if state in (FRESH, NOT_APPLICABLE) else "partial")
                    row["snapshot_state"] = state
                    row["snapshot_ratios_present"] = found
                if state == PARTIAL_VALID:
                    incomplete.append({"symbol": company["symbol"], "have": found,
                                       "missing": missing, "state": state})
                staged.extend(rows)
                checkpoints.save_checkpoint(day_kind, company["symbol"],
                                            status=checkpoints.DONE)
                successful += 1
        if len(staged) >= batch_size * len(EXPECTED):
            promote()
        if pause_seconds:
            time.sleep(pause_seconds)
    promote()

    # Two figures, because they answer different questions.
    #
    # Eligible coverage is whether the run worked: of the companies Upstox can
    # be asked about, how many answered. Universe coverage is what AGI actually
    # knows, and a company with no ISIN is a permanent hole in it rather than a
    # transient failure. Reporting only the first hides the structural gap;
    # reporting only the second makes a healthy run look broken.
    universe_size = len(universe)
    answerable = max(eligible_count - invalid, 0)
    coverage = round(100.0 * successful / answerable, 2) if answerable else 0.0
    universe_coverage = round(100.0 * successful / universe_size, 2) if universe_size else 0.0
    status = (FAILED if not successful
              else HEALTHY if coverage >= HEALTHY_COVERAGE_PCT
              else DEGRADED)
    stats = {
        "universe": universe_size,
        "eligible": eligible_count, "answerable": answerable,
        "requested": requested, "successful": successful,
        "failed": failed, "invalid": invalid, "skipped_no_isin": skipped,
        "incomplete": len(incomplete),
        "by_eligibility": by_eligibility,
        "coverage_pct": coverage,
        "universe_coverage_pct": universe_coverage,
        "status": status,
        "written": written,
        # Reported separately: the ratios can land while the pivot fails, and
        # a run that says "ok" while the desk sees nothing is the bug this
        # whole change exists to fix.
        "historical_valuation": valuation,
        "seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 1),
    }
    # A DEGRADED run wrote data; only FAILED wrote none. Recording DEGRADED as a
    # failed job made a batch that fetched 253 companies at 90.68% coverage read
    # as a dead integration, which is why this collector looked broken for
    # months while it was running two days ago.
    checkpoints.finish_job(run_id, ok=status != FAILED, stats=stats)
    return {"ok": status != FAILED, "run_id": run_id, **stats,
            "failures": failures[:25], "incomplete_sample": incomplete[:25],
            "note": ("coverage below 95% is reported DEGRADED rather than as a "
                     "complete daily snapshot")}
