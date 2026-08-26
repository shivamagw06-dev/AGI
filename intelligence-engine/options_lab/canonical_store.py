"""Writing canonical EOD option observations into Supabase.

Postgres rather than the engine's disk, because this grows by roughly 8.8M rows
a year and the engine's /var/data holds the live intraday evidence, which is a
different dataset with a different lifetime and a much smaller size.

Access is PostgREST with the service role, matching how everything else here
reaches Supabase. That has one consequence worth stating: PostgREST cannot run
DDL, so the table, its partitions and its indexes come from the migration in
supabase/migrations, not from this module. What this module does is call the
partition helper before writing a month it has not written before, so a new
month does not wait on someone remembering.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional

TABLE = "option_eod_observation"

# Bumped when the derivation changes in a way that makes new rows
# incomparable with old ones -- forward inference, rate assumption, gates.
PIPELINE_VERSION = "nse-eod-1"
# Bumped when the pricing or solver changes.
PRICING_VERSION = "black76-1"

# PostgREST holds the whole request in memory and Supabase caps the body size;
# a day is ~35,000 rows, so it goes up in pieces.
BATCH = 1000


class CanonicalStoreError(RuntimeError):
    pass


def _credentials() -> tuple[str, str]:
    url = (os.environ.get("SUPABASE_URL")
           or os.environ.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise CanonicalStoreError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return url, key


def _call(method: str, path: str, *, body: Any = None, prefer: str = "",
          timeout: float = 60.0, want_headers: bool = False) -> Any:
    url, key = _credentials()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(
        f"{url}{path}",
        data=None if body is None else json.dumps(body).encode("utf-8"),
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            payload = json.loads(raw) if raw else None
            if want_headers:
                return payload, dict(response.headers)
            return payload
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise CanonicalStoreError(f"{method} {path} failed ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise CanonicalStoreError(f"{method} {path} failed: {exc}") from exc


def ensure_partition(day: date | str) -> str:
    """Ask for the month's partition, and do not treat a refusal as fatal.

    Creating a partition creates a table, which needs CREATE on schema public.
    service_role does not hold that on a current Supabase project, so this call
    can answer 42501 even though the partition it wanted already exists --
    partitions are pre-created by migration for years either side of today.

    Failing the whole ingest on that would be refusing to write 828 good rows
    because a helper that had nothing to do was not allowed to do it. If the
    partition genuinely is missing, the insert that follows fails on its own
    and says so, which is the honest place for that error to surface.
    """
    day = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
    try:
        result = _call("POST", "/rest/v1/rpc/ensure_option_eod_partition",
                       body={"target": day.isoformat()})
    except CanonicalStoreError as exc:
        return f"unavailable: {str(exc)[:120]}"
    return str(result) if result else ""


def to_row(record: dict[str, Any]) -> dict[str, Any]:
    """One derived observation as the canonical table stores it.

    Greeks are dropped here rather than never computed: the live path wants
    them, and they are functions of columns that are kept, so persisting them
    would cost storage on every row to save arithmetic the research layer can
    redo.
    """
    return {
        "observation_date": record["trade_date"],
        "underlying_symbol": record["underlying"],
        "expiry": record["expiry"],
        "strike": record["strike"],
        "option_type": record["option_type"],
        "dte_days": record["dte_days"],
        "open_price": record.get("open"),
        "high_price": record.get("high"),
        "low_price": record.get("low"),
        "close_price": record.get("close"),
        "settlement_price": record.get("settlement"),
        "volume": int(record["volume"]) if record.get("volume") is not None else None,
        "open_interest": (int(record["open_interest"])
                          if record.get("open_interest") is not None else None),
        "change_open_interest": (int(record["change_in_oi"])
                                 if record.get("change_in_oi") is not None else None),
        "underlying_spot": record.get("underlying_close"),
        "forward": record["forward"],
        "forward_source": record["forward_source"],
        "forward_quality": record["forward_quality"],
        "forward_pair_count": record.get("forward_pair_count"),
        "forward_dispersion_bp": record.get("forward_dispersion_bp"),
        "moneyness": record.get("moneyness"),
        "log_moneyness": record.get("log_moneyness"),
        "implied_volatility": record.get("iv"),
        "iv_quality": record.get("iv_quality") or "unsolved",
        "isin": record.get("isin"),
        "source": "nse_bhavcopy",
        "pipeline_version": PIPELINE_VERSION,
        "pricing_version": PRICING_VERSION,
    }


def upsert(records: Iterable[dict[str, Any]], *, dry_run: bool = True) -> dict[str, Any]:
    """Write observations, replacing any already stored for the same contract-day.

    Re-ingesting a day must correct it, not double it, so this resolves on the
    natural key rather than inserting blindly. That also makes a re-run after a
    pipeline change the way history gets restated.
    """
    rows = [to_row(r) for r in records]
    if not rows:
        return {"ok": True, "rows": 0, "written": 0, "dry_run": dry_run,
                "note": "nothing to write"}

    days = sorted({r["observation_date"] for r in rows})
    summary = {
        "ok": True,
        "rows": len(rows),
        "days": days,
        "batches": (len(rows) + BATCH - 1) // BATCH,
        "pipeline_version": PIPELINE_VERSION,
        "pricing_version": PRICING_VERSION,
        "dry_run": dry_run,
    }
    if dry_run:
        summary["sample"] = rows[0]
        summary["note"] = "dry run: nothing written"
        return summary

    partitions = sorted({ensure_partition(d) for d in days})
    written = 0
    for start in range(0, len(rows), BATCH):
        chunk = rows[start:start + BATCH]
        _call("POST", f"/rest/v1/{TABLE}", body=chunk,
              prefer="resolution=merge-duplicates,return=minimal")
        written += len(chunk)
    summary.update({"written": written, "partitions": partitions,
                    "completed_at": datetime.now(timezone.utc).isoformat()})
    return summary


def stored_for_day(day: date | str, underlying: Optional[str] = None) -> int:
    """How many rows the table already holds for a day.

    PostgREST answers a HEAD count in the Content-Range header rather than the
    body, as `start-end/total`. Reading it beats fetching rows to measure them,
    which for a full day would be 35,000 rows pulled back to learn one number.
    """
    day = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
    query = f"?observation_date=eq.{day.isoformat()}&select=observation_date&limit=1"
    if underlying:
        query += f"&underlying_symbol=eq.{underlying}"
    _, headers = _call("GET", f"/rest/v1/{TABLE}{query}",
                       prefer="count=exact", want_headers=True)
    total = str(headers.get("Content-Range") or "").rsplit("/", 1)[-1]
    return int(total) if total.isdigit() else 0


SURFACE_TABLE = "option_surface_eod"


def observations_for_day(day: date | str, underlying: Optional[str] = None,
                         *, limit: int = 60000,
                         usable_iv_only: bool = True) -> list[dict[str, Any]]:
    """Read back a day's canonical rows, for the research layer to build on.

    Only the columns a surface needs. Pulling the whole row would move several
    megabytes to compute a dozen numbers from it.
    """
    day = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
    cols = ("observation_date,underlying_symbol,expiry,strike,option_type,"
            "dte_days,implied_volatility,iv_quality,forward,forward_quality,"
            # Positioning and the spot series read these. Leaving them out of
            # the select does not fail: the rows arrive, the keys are simply
            # absent, and every number built from them is null. That is how
            # spot stayed empty on fifty-nine days while nothing errored.
            "underlying_spot,volume,open_interest,change_open_interest")
    query = f"?observation_date=eq.{day.isoformat()}&select={cols}&limit={limit}"
    if usable_iv_only:
        # Right for fitting a smile, wrong for counting open interest: a
        # contract whose volatility could not be solved still carries a real
        # position, and dropping it biases every put-call ratio and max pain
        # toward the strikes that happened to price cleanly.
        query += "&iv_quality=eq.ok"
    if underlying:
        query += f"&underlying_symbol=eq.{underlying}"
    return _call("GET", f"/rest/v1/{TABLE}{query}") or []


def upsert_surfaces(surfaces: list[dict[str, Any]], *,
                    dry_run: bool = True) -> dict[str, Any]:
    """Write fitted surfaces, replacing any already stored for the same day."""
    if not surfaces:
        return {"ok": True, "rows": 0, "written": 0, "dry_run": dry_run,
                "note": "nothing to write"}
    rows = [{**s, "source": "nse_bhavcopy",
             "pipeline_version": PIPELINE_VERSION,
             "pricing_version": PRICING_VERSION} for s in surfaces]
    summary = {"ok": True, "rows": len(rows), "dry_run": dry_run,
               "surface_version": rows[0].get("surface_version")}
    if dry_run:
        summary["sample"] = rows[0]
        summary["note"] = "dry run: nothing written"
        return summary
    written = 0
    for start in range(0, len(rows), BATCH):
        chunk = rows[start:start + BATCH]
        _call("POST", f"/rest/v1/{SURFACE_TABLE}", body=chunk,
              prefer="resolution=merge-duplicates,return=minimal")
        written += len(chunk)
    summary["written"] = written
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    return summary


STATE_TABLE = "options_market_state_eod"


def spot_history(upto: date | str, underlying: str = "NIFTY",
                 *, days: int = 40) -> list[tuple[str, float]]:
    """Closing spot for the trading days up to and including a date.

    Read one row per day, not one row per contract. The obvious query -- select
    the spot column from the observations over the last forty days -- asks for
    roughly fifty thousand rows to extract forty numbers, and PostgREST caps
    what it returns. The cap is silent: the call succeeds, returns about a day
    of prices, and every realised volatility built from it comes back null.
    That is exactly what happened, on all fifty-nine days.

    So the state table answers first, since it already holds one spot per day,
    and the observations are asked only for the day being described, one row.

    Reads only what precedes the day in question. A realised volatility built
    from a window reaching past it would be accurate and untradeable.
    """
    upto = upto if isinstance(upto, date) else date.fromisoformat(str(upto)[:10])
    start = date.fromordinal(upto.toordinal() - days * 2)
    history: dict[str, float] = {}

    query = (f"?observation_date=gte.{start.isoformat()}"
             f"&observation_date=lte.{upto.isoformat()}"
             f"&underlying_symbol=eq.{underlying}"
             f"&select=observation_date,spot&order=observation_date.asc"
             f"&limit={days * 2}")
    try:
        for row in _call("GET", f"/rest/v1/{STATE_TABLE}{query}") or []:
            if row.get("spot"):
                history[str(row["observation_date"])] = float(row["spot"])
    except CanonicalStoreError:
        # The state table may not exist yet on a first build. The day's own
        # spot below is enough to store the row; realised volatility simply
        # stays null until there are prior days to measure against.
        pass

    if upto.isoformat() not in history:
        one = _call("GET", f"/rest/v1/{TABLE}"
                           f"?observation_date=eq.{upto.isoformat()}"
                           f"&underlying_symbol=eq.{underlying}"
                           f"&select=underlying_spot&limit=1") or []
        if one and one[0].get("underlying_spot"):
            history[upto.isoformat()] = float(one[0]["underlying_spot"])

    return sorted(history.items())[-days:]


def surfaces_for_day(day: date | str, underlying: str = "NIFTY") -> list[dict[str, Any]]:
    day = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
    query = (f"?observation_date=eq.{day.isoformat()}"
             f"&underlying_symbol=eq.{underlying}&limit=500")
    return _call("GET", f"/rest/v1/{SURFACE_TABLE}{query}") or []


def upsert_state(state: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    row = {**state, "source": "nse_bhavcopy", "pipeline_version": PIPELINE_VERSION}
    if dry_run:
        return {"ok": True, "rows": 1, "dry_run": True, "sample": row,
                "note": "dry run: nothing written"}
    _call("POST", f"/rest/v1/{STATE_TABLE}", body=[row],
          prefer="resolution=merge-duplicates,return=minimal")
    return {"ok": True, "rows": 1, "written": 1, "dry_run": False,
            "completed_at": datetime.now(timezone.utc).isoformat()}
