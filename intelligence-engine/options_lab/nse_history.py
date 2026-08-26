"""Daily option history from the NSE F&O bhavcopy.

A separate research dataset, not a replacement for the intraday collector. The
two answer different questions and must not be merged:

  intraday collector -> "can the model reprice a contract 5-30 minutes later?"
  this               -> "did a signal carry information from one close to the next?"

Bhavcopy is end-of-day only. It gives open, high, low and close but not the
path between them, so nothing here can support "signal at 11:15, exit at 14:15".
Every study built on this is EOD to EOD, and saying so in the module is cheaper
than discovering it in a backtest that looked profitable.

What it does give, free and without a subscription, is years of every listed
contract: strike, expiry, OHLC, volume, open interest, the change in open
interest, and the underlying close on the same row.

The forward is the part worth reading carefully. See `forward_for_expiry`.
"""

from __future__ import annotations

import csv
import io
import math
import statistics
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Optional

from .engine import _implied_volatility, _greeks

ARCHIVE = ("https://nsearchives.nseindia.com/content/fo/"
           "BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip")

# NSE serves the archive only to something that looks like a browser.
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

OPTION_TYPES = ("CE", "PE")
# IDO/STO are index and stock options; IDF/STF the matching futures.
OPTION_KINDS = ("IDO", "STO")
FUTURE_KINDS = ("IDF", "STF")

DEFAULT_RATE_PCT = 5.25


class NseHistoryError(RuntimeError):
    pass


# A parity forward built from one strike pair is a guess dressed as a
# measurement. These bound what counts as trustworthy.
PARITY_BAND = 0.06          # keep pairs within 6% of the money
MIN_PAIRS_HIGH = 5
MAX_DISPERSION_HIGH_BP = 25.0
MAX_DISPERSION_ANY_BP = 200.0

# Outside these an implied volatility is a solver artefact, not a market view.
IV_FLOOR_PCT = 0.5
IV_CEILING_PCT = 300.0
MIN_DTE_DAYS = 1


@dataclass(frozen=True)
class Forward:
    """The forward price used to imply volatility, and how much to trust it."""
    value: float
    source: str                       # future | parity | spot
    quality: str                      # high | medium | low
    strike: Optional[float] = None
    basis_pct: Optional[float] = None
    pair_count: int = 0
    dispersion_bp: Optional[float] = None


def fetch_bhavcopy(day: date | str, *, timeout: int = 60) -> list[dict[str, str]]:
    """One trading day of F&O rows. Raises if NSE has no file for that date."""
    day = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
    url = ARCHIVE.format(yyyymmdd=day.strftime("%Y%m%d"))
    request = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            blob = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            # Weekend, holiday, or a date before the current file naming.
            raise NseHistoryError(f"no bhavcopy for {day.isoformat()}") from error
        raise NseHistoryError(f"HTTP {error.code} for {day.isoformat()}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise NseHistoryError(f"fetch failed for {day.isoformat()}: {error}") from error

    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise NseHistoryError(f"no csv inside the archive for {day.isoformat()}")
        text = archive.read(names[0]).decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def _f(row: dict[str, str], key: str) -> Optional[float]:
    try:
        value = float(str(row.get(key) or "").strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _traded(row: dict[str, str]) -> bool:
    """Did this contract actually trade today?

    A contract with no volume still carries a close, but it is a settlement
    price NSE derives rather than a price anyone paid. Implying volatility from
    those manufactures a surface out of NSE's own model instead of the market's,
    and on a typical day most of the chain has never traded.
    """
    volume = _f(row, "TtlTradgVol")
    return bool(volume and volume > 0)


def year_fraction(trade_day: date, expiry: date) -> float:
    """Calendar years to expiry, floored just above zero.

    Expiry day itself is 0, which no pricing model can divide by; those rows are
    excluded by the caller rather than smoothed into a fictitious lifetime.
    """
    days = (expiry - trade_day).days
    return days / 365.0 if days > 0 else 0.0


def forward_for_expiry(rows: Iterable[dict[str, str]], *,
                       rate_pct: float = DEFAULT_RATE_PCT) -> Optional[Forward]:
    """The forward price for one underlying and expiry, and how much to trust it.

    Order matters. A traded future IS the market's forward -- someone paid that
    price for it -- so where one exists it is authoritative and nothing is
    inferred. Parity is what covers the expiries that have no future, which for
    NIFTY is most of them: eighteen option expiries against three monthly
    futures.

    Spot is never right and the file tempts you with it, since UndrlygPric sits
    on every row. On 21 Aug 2026 NIFTY spot was 24,252 while the October future
    closed at 24,521.90 -- a 1.1% basis that would bias every implied volatility
    on that expiry, worst at the wings. It stays only as a labelled last resort.

    The parity forward is a median over several near-money strike pairs rather
    than the single closest one. F = K + e^{rT}(C - P) holds at every strike, so
    disagreement between strikes measures how stale the quotes are. One pair
    cannot show that disagreement, which is exactly when it is most dangerous.
    The spread across pairs is reported so a study can require agreement rather
    than trust a number that happens to exist.
    """
    rows = list(rows)
    if not rows:
        return None
    spot = next((_f(r, "UndrlygPric") for r in rows if _f(r, "UndrlygPric")), None)

    first = rows[0]
    try:
        trade_day = date.fromisoformat(str(first["TradDt"])[:10])
        expiry = date.fromisoformat(str(first["XpryDt"])[:10])
    except (KeyError, ValueError):
        return None
    time_years = year_fraction(trade_day, expiry)
    if time_years <= 0:
        return None

    def basis_of(value: float) -> Optional[float]:
        return ((value / spot - 1.0) * 100.0) if spot else None

    # 1. A traded future is the market's own answer.
    future = next((_f(r, "ClsPric") for r in rows
                   if r.get("FinInstrmTp") in FUTURE_KINDS
                   and _traded(r) and _f(r, "ClsPric")), None)
    if future and future > 0:
        return Forward(future, "future", "high", basis_pct=basis_of(future))

    # 2. Parity across the near-money strikes that actually traded.
    calls: dict[float, float] = {}
    puts: dict[float, float] = {}
    for row in rows:
        if not _traded(row):
            continue
        strike = _f(row, "StrkPric")
        close = _f(row, "ClsPric")
        if not strike or close is None:
            continue
        if row.get("OptnTp") == "CE":
            calls[strike] = close
        elif row.get("OptnTp") == "PE":
            puts[strike] = close

    both = sorted(set(calls) & set(puts))
    if both:
        carry = math.exp(rate_pct / 100.0 * time_years)
        # Anchor the band on the crossover strike, where |C - P| is smallest.
        # Using spot would centre the band on the wrong place exactly when the
        # basis is large, which is when this matters.
        anchor = min(both, key=lambda k: abs(calls[k] - puts[k]))
        near = [k for k in both if abs(k / anchor - 1.0) <= PARITY_BAND] or [anchor]
        implied = sorted(k + carry * (calls[k] - puts[k]) for k in near)
        implied = [f for f in implied if f > 0]
        if implied:
            forward = statistics.median(implied)
            spread_bp = ((max(implied) - min(implied)) / forward * 10000.0
                         if forward else None)
            if len(implied) == 1:
                quality = "low"
            elif (len(implied) >= MIN_PAIRS_HIGH
                  and spread_bp is not None and spread_bp <= MAX_DISPERSION_HIGH_BP):
                quality = "high"
            elif spread_bp is not None and spread_bp <= MAX_DISPERSION_ANY_BP:
                quality = "medium"
            else:
                quality = "low"
            return Forward(forward, "parity", quality, strike=anchor,
                           basis_pct=basis_of(forward), pair_count=len(implied),
                           dispersion_bp=round(spread_bp, 2) if spread_bp is not None else None)

    # 3. Labelled last resort.
    if spot:
        return Forward(spot, "spot", "low", basis_pct=0.0)
    return None


def _implied(kind: str, close: float, strike: float, forward: Forward,
             time_years: float, dte: int,
             rate_pct: float) -> tuple[Optional[float], str]:
    """Implied volatility, or the reason there isn't one.

    Every gate returns a named refusal rather than a clamped number. A volatility
    pinned to a bound looks like data and behaves like data, and one that reaches
    a percentile study drags the whole distribution with it. A study can filter
    on the reason; it cannot recover from a fabricated value.
    """
    if dte < MIN_DTE_DAYS:
        return None, "expiring"
    if forward.value <= 0:
        return None, "no_forward"

    # Below intrinsic there is no volatility that prices this, only a stale or
    # mismarked close. Solvers answer anyway, at the floor.
    intrinsic = (max(0.0, forward.value - strike) if kind == "call"
                 else max(0.0, strike - forward.value))
    discounted = intrinsic * math.exp(-rate_pct / 100.0 * time_years)
    if close < discounted - max(0.05, 0.001 * strike):
        return None, "below_intrinsic"

    solved = _implied_volatility(close, kind, forward.value, strike, time_years,
                                 rate_pct / 100.0, rate_pct / 100.0)
    if not solved:
        return None, "unsolved"
    pct = solved * 100.0
    if pct <= IV_FLOOR_PCT or pct >= IV_CEILING_PCT:
        return None, "implausible"
    if forward.quality == "low":
        # The number solved, but against a forward nothing corroborates.
        return solved, "weak_forward"
    return solved, "ok"


def option_records(rows: Iterable[dict[str, str]], *,
                   underlyings: Optional[set[str]] = None,
                   rate_pct: float = DEFAULT_RATE_PCT,
                   traded_only: bool = True,
                   with_greeks: bool = True) -> list[dict[str, Any]]:
    """Bhavcopy rows to option observations with implied volatility and greeks.

    Volatility is implied against the forward, using Black-76. The engine here
    is the same one the live collector prices with -- passing the forward as
    spot with the dividend yield set equal to the rate reduces its
    Black-Scholes exactly to Black-76 -- so historical and live IV are the same
    quantity and can be compared without a second pricer to keep in step.
    """
    rows = list(rows)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        symbol = str(row.get("TckrSymb") or "").strip()
        if underlyings and symbol not in underlyings:
            continue
        if row.get("FinInstrmTp") not in OPTION_KINDS + FUTURE_KINDS:
            continue
        grouped.setdefault((symbol, str(row.get("XpryDt") or "")[:10]), []).append(row)

    out: list[dict[str, Any]] = []
    for (symbol, expiry_text), chain in grouped.items():
        forward = forward_for_expiry(chain, rate_pct=rate_pct)
        if not forward:
            continue
        try:
            trade_day = date.fromisoformat(str(chain[0]["TradDt"])[:10])
            expiry = date.fromisoformat(expiry_text)
        except (KeyError, ValueError):
            continue
        time_years = year_fraction(trade_day, expiry)
        if time_years <= 0:
            continue

        for row in chain:
            if row.get("OptnTp") not in OPTION_TYPES:
                continue
            if traded_only and not _traded(row):
                continue
            dte = (expiry - trade_day).days
            strike = _f(row, "StrkPric")
            close = _f(row, "ClsPric")
            if not strike or close is None or close <= 0:
                continue
            kind = "call" if row["OptnTp"] == "CE" else "put"
            iv, iv_quality = _implied(kind, close, strike, forward,
                                      time_years, dte, rate_pct)
            greeks = {}
            if iv and with_greeks:
                greeks = _greeks(kind, forward.value, strike, time_years,
                                 rate_pct / 100.0, rate_pct / 100.0, iv) or {}
            out.append({
                "trade_date": trade_day.isoformat(),
                "underlying": symbol,
                "expiry": expiry.isoformat(),
                "strike": strike,
                "option_type": row["OptnTp"],
                "dte_days": dte,
                "open": _f(row, "OpnPric"),
                "high": _f(row, "HghPric"),
                "low": _f(row, "LwPric"),
                "close": close,
                "settlement": _f(row, "SttlmPric"),
                "volume": _f(row, "TtlTradgVol"),
                "open_interest": _f(row, "OpnIntrst"),
                "change_in_oi": _f(row, "ChngInOpnIntrst"),
                "underlying_close": _f(row, "UndrlygPric"),
                "forward": round(forward.value, 4),
                "forward_source": forward.source,
                "moneyness": round(strike / forward.value, 6),
                "log_moneyness": round(math.log(strike / forward.value), 6),
                "iv": round(iv * 100.0, 4) if iv else None,
                "iv_quality": iv_quality,
                "forward_quality": forward.quality,
                "forward_pair_count": forward.pair_count,
                "forward_dispersion_bp": forward.dispersion_bp,
                "delta": greeks.get("delta"),
                "gamma": greeks.get("gamma"),
                "theta": greeks.get("theta_per_day"),
                "vega": greeks.get("vega_per_vol_point"),
                "isin": (row.get("ISIN") or "").strip() or None,
            })
    return out


def probe(day: date | str = "2026-08-21", underlying: str = "NIFTY") -> dict[str, Any]:
    """Read one real day end to end and report what came out.

    Read-only. Exists so the derivation can be checked against a known day
    before anything is written to disk.
    """
    try:
        rows = fetch_bhavcopy(day)
    except NseHistoryError as exc:
        return {"ok": False, "stage": "fetch", "error": str(exc)[:200]}

    records = option_records(rows, underlyings={underlying})
    if not records:
        return {"ok": False, "stage": "derive", "rows": len(rows),
                "error": f"no traded {underlying} options derived"}

    with_iv = [r for r in records if r["iv"]]
    expiries = sorted({r["expiry"] for r in records})
    sources = {}
    for r in records:
        sources[r["forward_source"]] = sources.get(r["forward_source"], 0) + 1
    front = [r for r in with_iv if r["expiry"] == expiries[0]]
    atm = min(front, key=lambda r: abs(r["log_moneyness"])) if front else None
    return {
        "ok": True,
        "stage": "complete",
        "trade_date": records[0]["trade_date"],
        "file_rows": len(rows),
        "traded_options": len(records),
        "with_iv": len(with_iv),
        "expiries": len(expiries),
        "forward_sources": sources,
        "atm_front": {
            k: atm[k] for k in ("expiry", "strike", "option_type", "close",
                                "forward", "underlying_close", "iv", "delta",
                                "open_interest", "change_in_oi")
        } if atm else None,
    }


def ingest_day(day: date | str, *, underlyings: Optional[set[str]] = None,
               dry_run: bool = True) -> dict[str, Any]:
    """One trading day from NSE into the canonical warehouse.

    Greeks are not computed here. They are functions of columns the table keeps,
    so the research layer derives them; paying for 35,000 of them on the way in
    buys nothing that is stored.

    Defaults to a dry run. An ingest that writes on a bare call is how a
    methodology change quietly restates history.
    """
    from . import canonical_store

    try:
        rows = fetch_bhavcopy(day)
    except NseHistoryError as exc:
        return {"ok": False, "stage": "fetch", "error": str(exc)[:200]}

    records = option_records(rows, underlyings=underlyings, with_greeks=False)
    if not records:
        return {"ok": False, "stage": "derive", "file_rows": len(rows),
                "error": "no traded options derived"}

    quality: dict[str, int] = {}
    for r in records:
        quality[r["iv_quality"]] = quality.get(r["iv_quality"], 0) + 1
    try:
        written = canonical_store.upsert(records, dry_run=dry_run)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "write", "derived": len(records),
                "error": str(exc)[:300]}
    return {"ok": True, "stage": "complete", "file_rows": len(rows),
            "derived": len(records), "iv_quality": quality, "write": written}


# NSE serves these from an archive, not an API, and a tight loop over a hundred
# files gets throttled. Slow enough to be a good citizen, fast enough that a
# chunk finishes inside one request.
PAUSE_SECONDS = 2.0

# A backfill of six months takes roughly twenty minutes of fetching, which is
# longer than the engine will hold a request open. So a call does a bounded
# chunk and says where it stopped; calling again continues from there, because
# days already stored are skipped.
DEFAULT_MAX_DAYS = 10


def trading_days(start: date | str, end: date | str) -> list[date]:
    """Weekdays between two dates, inclusive.

    Holidays are not known here and are not guessed: NSE simply has no file for
    one, which the fetch reports as a 404 and the backfill records as a holiday.
    Guessing a calendar would be one more thing to keep correct.
    """
    start = start if isinstance(start, date) else date.fromisoformat(str(start)[:10])
    end = end if isinstance(end, date) else date.fromisoformat(str(end)[:10])
    out, day = [], start
    while day <= end:
        if day.weekday() < 5:
            out.append(day)
        day = date.fromordinal(day.toordinal() + 1)
    return out


def backfill(start: date | str, end: date | str, *,
             underlyings: Optional[set[str]] = None,
             dry_run: bool = True,
             max_days: int = DEFAULT_MAX_DAYS,
             pause_seconds: float = PAUSE_SECONDS,
             skip_existing: bool = True) -> dict[str, Any]:
    """Walk trading days into the warehouse, a chunk at a time.

    Resumable by construction rather than by bookkeeping: a day already holding
    rows is skipped, so the only state the next call needs is what the table
    already contains. Nothing to corrupt, and a half-finished run is just a
    shorter next run.

    One bad day does not stop the walk. A holiday has no file, and a single
    malformed day should not strand the ninety after it -- both are recorded
    and the loop continues.
    """
    import time

    from . import canonical_store

    days = trading_days(start, end)
    done: list[dict[str, Any]] = []
    skipped: list[str] = []
    holidays: list[str] = []
    failed: list[dict[str, str]] = []
    written_total = 0
    stopped_before: Optional[str] = None

    for index, day in enumerate(days):
        if len(done) >= max_days:
            stopped_before = day.isoformat()
            break

        iso = day.isoformat()
        if skip_existing and not dry_run:
            try:
                if canonical_store.stored_for_day(
                        day, next(iter(underlyings)) if underlyings and
                        len(underlyings) == 1 else None) > 0:
                    skipped.append(iso)
                    continue
            except canonical_store.CanonicalStoreError as exc:
                failed.append({"day": iso, "stage": "check", "error": str(exc)[:160]})
                continue

        if done or failed:
            time.sleep(pause_seconds)

        try:
            rows = fetch_bhavcopy(day)
        except NseHistoryError as exc:
            # No file is the normal shape of a holiday, not a failure.
            if "no bhavcopy" in str(exc):
                holidays.append(iso)
            else:
                failed.append({"day": iso, "stage": "fetch", "error": str(exc)[:160]})
            continue

        records = option_records(rows, underlyings=underlyings, with_greeks=False)
        if not records:
            failed.append({"day": iso, "stage": "derive",
                           "error": "no traded options derived"})
            continue

        try:
            result = canonical_store.upsert(records, dry_run=dry_run)
        except canonical_store.CanonicalStoreError as exc:
            failed.append({"day": iso, "stage": "write", "error": str(exc)[:160]})
            continue

        written = int(result.get("written") or 0)
        written_total += written
        done.append({"day": iso, "derived": len(records), "written": written})

    remaining = [d.isoformat() for d in days
                 if stopped_before and d.isoformat() >= stopped_before]
    return {
        "ok": not failed,
        "requested": {"start": str(start)[:10], "end": str(end)[:10],
                      "trading_days": len(days)},
        "ingested": done,
        "written_total": written_total,
        "skipped_already_present": skipped,
        "holidays": holidays,
        "failed": failed,
        "dry_run": dry_run,
        # What to pass next time. Present only when the chunk limit stopped it.
        "resume_from": stopped_before,
        "remaining_days": len(remaining),
    }
