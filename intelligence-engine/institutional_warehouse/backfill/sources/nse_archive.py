"""NSE bhavcopy archive walker.

The live collector answers "what happened today" and re-answers it every cycle.
This walks the archive the other way: newest missing day first, then the day
before that, until the archive runs out or the budget does.

A date is fetched once. ``wh_backfill_dates`` remembers the outcome, so a
completed day is never downloaded again and a dead day (holiday, gap in the
archive) is retired after a few attempts instead of being retried forever.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Optional

from institutional_warehouse import gateway, store
from institutional_warehouse.backfill import checkpoints
from institutional_warehouse.values import to_date, to_number

SOURCE = "nse_bhavcopy"

# NSE's full bhavdata file starts in 2016; the older zipped cm<DDMMMYYYY>bhav.csv
# archive reaches back to the 1990s. Both patterns are tried per date.
ARCHIVE_FLOOR = date(1995, 1, 1)


def trading_days_backwards(
    *,
    start: Optional[date] = None,
    floor: Optional[date] = None,
    limit: int = 400,
) -> list[str]:
    """Weekday calendar walking backwards from ``start``. Holidays fall out naturally
    when the fetch 404s and the date is retired."""
    cursor = start or datetime.now(timezone.utc).date()
    stop = floor or ARCHIVE_FLOOR
    out: list[str] = []
    while cursor >= stop and len(out) < max(1, int(limit)):
        if cursor.weekday() < 5:
            out.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    return out


def archive_urls(trade_date: str) -> list[str]:
    moment = datetime.strptime(trade_date, "%Y-%m-%d")
    dd = moment.strftime("%d")
    mmm = moment.strftime("%b").upper()
    mon = moment.strftime("%m")
    yyyy = moment.strftime("%Y")
    return [
        f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{dd}{mon}{yyyy}.csv",
        f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{dd}{mon}{yyyy}.csv",
        f"https://archives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip",
        f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip",
    ]


def _default_fetch(url: str) -> bytes:
    from live_data.collectors.base import http_get

    return http_get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AGIB-Backfill/1.0)",
            "Accept": "*/*",
            "Referer": "https://www.nseindia.com/",
        },
        timeout=30,
    )


def _csv_bytes(payload: bytes) -> bytes:
    if payload[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("zip_without_csv")
            return archive.read(names[0])
    return payload


# Which series count as a company's shares.
#
# This collector exists to fix survivorship bias - the warehouse holds only
# companies that still trade, so a backtest never takes the losses from ones
# that failed. It kept EQ and BE, and that quietly excluded the failures it was
# built to capture: a company on its way out is moved to BZ, the surveillance
# series, before it is delisted. Cox & Kings sat in BZ at 1.25 rupees on 15 June
# 2020 and was dropped on every pass.
#
# SM and ST are the SME board. Those companies delist too, and leaving them out
# repeats the same bias one tier down.
#
# An allow-list rather than a deny-list on purpose. Around ninety other series
# codes appear across the archive - GB and GS are government paper, N1 through
# NZ and the Y and Z ranges are debt, RR is rights entitlements, MF is fund
# units - and NSE adds more over time. A deny-list would let each new one in
# silently. BL matters most of all: it is the block-deal window, a second price
# for a symbol on a day it already has one, and admitting it would overwrite the
# real close.
#
# Verified against six bhavcopies spanning 2016 to 2026: no symbol ever appears
# under two of these series on the same day, so widening the filter cannot
# collide on the (symbol, date) key.
EQUITY_SERIES = ("EQ", "BE", "BZ", "SM", "ST")


def parse_rows(text: str, trade_date: str) -> list[dict[str, Any]]:
    """Both bhavcopy layouts into warehouse market-history rows."""
    import csv

    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for raw in reader:
        record = {
            (k or "").strip().upper(): (v.strip() if isinstance(v, str) else v)
            for k, v in raw.items()
            if k
        }
        series = (record.get("SERIES") or "EQ").upper()
        if series not in EQUITY_SERIES:
            continue
        symbol = (record.get("SYMBOL") or "").strip().upper()
        if not symbol:
            continue
        close = to_number(record.get("CLOSE_PRICE") or record.get("CLOSE"))
        if close is None:
            continue
        observed = to_date(record.get("DATE1") or record.get("TIMESTAMP")) or trade_date
        rows.append(
            {
                "symbol": symbol,
                "date": observed,
                "open": to_number(record.get("OPEN_PRICE") or record.get("OPEN")),
                "high": to_number(record.get("HIGH_PRICE") or record.get("HIGH")),
                "low": to_number(record.get("LOW_PRICE") or record.get("LOW")),
                "close": close,
                "adjusted_close": close,
                "vwap": to_number(record.get("AVG_PRICE")),
                "volume": to_number(record.get("TTL_TRD_QNTY") or record.get("TOTTRDQTY")),
                "delivery_pct": to_number(record.get("DELIV_PER")),
                "source": SOURCE,
            }
        )
    return rows


def fetch_day(
    trade_date: str,
    *,
    fetch: Optional[Callable[[str], bytes]] = None,
) -> dict[str, Any]:
    """One trading day from the archive. Raises only when every URL pattern fails."""
    getter = fetch or _default_fetch
    errors: list[str] = []
    for url in archive_urls(trade_date):
        try:
            payload = getter(url)
        except Exception as exc:
            errors.append(f"{url.rsplit('/', 1)[-1]}:{type(exc).__name__}")
            continue
        if not payload:
            errors.append(f"{url.rsplit('/', 1)[-1]}:empty")
            continue
        body = _csv_bytes(payload)
        text = body.decode("utf-8", errors="replace")
        rows = parse_rows(text, trade_date)
        if not rows:
            errors.append(f"{url.rsplit('/', 1)[-1]}:no_rows")
            continue
        return {
            "ok": True,
            "trade_date": trade_date,
            "url": url,
            "rows": rows,
            "checksum": hashlib.sha256(body).hexdigest(),
        }
    return {"ok": False, "trade_date": trade_date, "rows": [], "errors": errors}


# What share of a slice goes to keeping up with new days. The rest digs.
#
# The two ends have to be claimed separately. Offering one combined list does
# not work: the recent end always sorts first, so it takes the whole slice and
# the deep end never gets a turn - which is the stall, not a fix for it.
RECENT_SHARE = 0.25


def _claim_both_ends(days: int, floor_date, max_attempts: int) -> list[str]:
    """Days from the top of the archive and days from where digging left off.

    One window cannot do both jobs. Counted from today the walk can never see
    further back than its own length - around eleven months at the scheduled
    slice size - while the archive runs to 1995. Counted only from the frontier
    it digs happily and never notices this morning's bhavcopy.
    """
    recent_budget = max(1, int(days * RECENT_SHARE))
    recent = checkpoints.claim_dates(
        SOURCE,
        trading_days_backwards(start=None, floor=floor_date, limit=max(days, 1)),
        limit=recent_budget, max_attempts=max_attempts)

    frontier = checkpoints.frontier_date(SOURCE)
    if not frontier:
        # Nothing collected yet, so there is no deep end to dig at. Spend the
        # whole slice at the top; the frontier appears as soon as a day lands.
        return checkpoints.claim_dates(
            SOURCE,
            trading_days_backwards(start=None, floor=floor_date, limit=max(days * 6, days)),
            limit=days, max_attempts=max_attempts)

    deep = checkpoints.claim_dates(
        SOURCE,
        trading_days_backwards(start=datetime.strptime(frontier, "%Y-%m-%d").date(),
                               floor=floor_date, limit=max(days * 6, days)),
        limit=max(days - len(recent), 1), max_attempts=max_attempts)

    seen: set[str] = set()
    return [d for d in (*recent, *deep) if not (d in seen or seen.add(d))]


def backfill(
    *,
    actor: str = "backfill",
    days: int = 60,
    start: Optional[str] = None,
    floor: Optional[str] = None,
    fetch: Optional[Callable[[str], bytes]] = None,
    max_attempts: int = checkpoints.MAX_ATTEMPTS,
) -> dict[str, Any]:
    """Walk the archive backwards, writing each new day into market history."""
    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    floor_date = datetime.strptime(floor, "%Y-%m-%d").date() if floor else None
    # Look at a wide calendar window but only claim the days still owed, so a
    # long-running backfill keeps making progress instead of re-walking the top.
    #
    # Two windows, because one cannot do both jobs. Counted from today the walk
    # can never see further back than its own length - around eleven months at
    # the scheduled slice size - and the archive goes to 1995. Counted only from
    # the frontier it digs happily and never notices this morning's bhavcopy.
    #
    # So: a short window at the top for days as they appear, and a long one from
    # the oldest day already collected, which moves back as the work advances.
    if start_date is not None:
        candidates = trading_days_backwards(start=start_date, floor=floor_date,
                                            limit=max(int(days) * 6, int(days)))
        claimed = checkpoints.claim_dates(SOURCE, candidates, limit=int(days),
                                          max_attempts=max_attempts)
    else:
        claimed = _claim_both_ends(int(days), floor_date, max_attempts)

    imported = 0
    written = {"inserted": 0, "updated": 0, "unchanged": 0}
    done: list[str] = []
    missing: list[str] = []

    for trade_date in claimed:
        result = fetch_day(trade_date, fetch=fetch)
        if not result.get("ok"):
            checkpoints.mark_date(SOURCE, trade_date, status=checkpoints.FAILED,
                                  error=",".join(result.get("errors") or [])[:200])
            missing.append(trade_date)
            continue
        rows = result["rows"]
        outcome = gateway.write("daily_market_history", rows, source=SOURCE, actor=actor,
                               reason=f"backfill:nse:{trade_date}")
        for key in written:
            written[key] += int(outcome.get(key) or 0)
        imported += len(rows)
        checkpoints.mark_date(SOURCE, trade_date, status=checkpoints.DONE,
                              rows=len(rows), checksum=result.get("checksum"))
        done.append(trade_date)

    coverage = checkpoints.date_coverage(SOURCE)
    return {
        "ok": True,
        "source": SOURCE,
        "claimed": len(claimed),
        "days_imported": len(done),
        "days_missing": len(missing),
        "rows_seen": imported,
        **written,
        "first": min(done) if done else None,
        "last": max(done) if done else None,
        "coverage": coverage,
    }
