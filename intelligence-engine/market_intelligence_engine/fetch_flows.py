"""Pull FII/DII activity from Upstox into the warehouse.

The fetcher already existed in the Express service and stopped working: its
Upstox token answers "Invalid token used to access API", and the FII/DII table
has not moved since 20 August. The engine's token is valid - the valuation
sweep collected 2,088 companies with it on the 23rd - so the fetch belongs
here, next to the credential that works.

The scheduler it replaces was also in-memory, targeting 18:05-18:59 IST on a
service that redeploys several times a day. Its own status reported
``lastRun: null``: every deploy reset the timer, so the window was only hit if
the process happened to be alive for it. This is called from the daily cron
instead, which does not depend on any process staying up.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from valuation_ratios.sweep import USER_AGENT, _token, safe_pause

BASE = "https://api.upstox.com/v2"
SOURCE = "upstox"

# The segments Upstox reports FII activity for. DII is cash only.
FII_SEGMENTS = (
    "NSE_EQ|CASH",
    "NSE_FO|INDEX_FUTURES",
    "NSE_FO|STOCK_FUTURES",
    "NSE_FO|INDEX_OPTIONS",
    "NSE_FO|STOCK_OPTIONS",
)
DII_SEGMENTS = ("NSE_EQ|CASH",)

# Money fields carried straight through; contract fields are FII-only.
CONTRACT_FIELDS = (
    "buy_contracts", "sell_contracts", "oi_contracts", "oi_amount",
    "total_long_contracts", "total_short_contracts",
    "total_call_long_contracts", "total_put_long_contracts",
    "total_call_short_contracts", "total_put_short_contracts",
)
CONTRACT_RENAMES = {
    "total_long_contracts": "long_contracts",
    "total_short_contracts": "short_contracts",
    "total_call_long_contracts": "call_long_contracts",
    "total_put_long_contracts": "put_long_contracts",
    "total_call_short_contracts": "call_short_contracts",
    "total_put_short_contracts": "put_short_contracts",
}


def _ist_date(timestamp: Any) -> Optional[str]:
    """Upstox stamps in epoch milliseconds; the trading day is IST.

    Reading it as UTC moves anything stamped after 18:30 IST onto the previous
    day, which is most of an end-of-day feed.
    """
    try:
        millis = float(timestamp)
    except (TypeError, ValueError):
        return None
    moment = datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc) + timedelta(hours=5, minutes=30)
    return moment.date().isoformat()


def _get(path: str, params: list[tuple[str, str]], *, timeout: float = 30.0) -> dict[str, Any]:
    token = _token()
    if not token:
        return {"ok": False, "error": "no_upstox_token"}
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    # The default urllib user agent is refused by Upstox's Cloudflare as a
    # blocked client fingerprint rather than an auth failure, which is why the
    # ratio sweep carries the same header.
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Api-Version": "2.0",
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {token}",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"ok": True, "payload": json.loads(response.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:  # noqa: BLE001 - the status is the useful part
            pass
        return {"ok": False, "error": f"http_{exc.code}", "detail": detail}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}


def _observations(payload: dict[str, Any], participant: str, interval: str) -> list[dict[str, Any]]:
    """Upstox rows to the observation shape normalise_upstox_flow expects."""
    data = payload.get("data")
    rows = data if isinstance(data, list) else (data or {}).get("data") if isinstance(data, dict) else None
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        observed = _ist_date(row.get("time_stamp") if row.get("time_stamp") is not None
                             else row.get("timestamp"))
        if not observed:
            continue
        item = {
            "participant": participant,
            "segment": str(row.get("data_type") or row.get("segment") or "NSE_EQ|CASH")[:32],
            "interval": interval,
            "observation_date": observed,
            "time_stamp": row.get("time_stamp") or row.get("timestamp"),
            "buy_amount": row.get("buy_amount"),
            "sell_amount": row.get("sell_amount"),
        }
        if participant == "FII":
            for field in CONTRACT_FIELDS:
                item[CONTRACT_RENAMES.get(field, field)] = row.get(field)
        out.append(item)
    return out


def fetch(*, interval: str = "1D", since: Optional[str] = None,
          pause_seconds: Optional[float] = None) -> dict[str, Any]:
    """Every FII and DII observation Upstox will give us, as observations."""
    # A window rather than one day: the feed publishes after close and a
    # missed run should be recovered by the next one, not lost. The warehouse
    # key is (date, segment) so re-fetching a day already held updates it.
    start = since or (date.today() - timedelta(days=10)).isoformat()
    pause = safe_pause(pause_seconds)

    observations: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for participant, segments, path in (("FII", FII_SEGMENTS, "/market/fii"),
                                        ("DII", DII_SEGMENTS, "/market/dii")):
        params = [("data_type", s) for s in segments]
        params += [("interval", interval), ("from", start)]
        result = _get(path, params)
        if not result.get("ok"):
            failures.append({"participant": participant, **{k: v for k, v in result.items() if k != "ok"}})
            continue
        observations.extend(_observations(result.get("payload") or {}, participant, interval))
        if pause:
            import time

            time.sleep(pause)

    days = sorted({o["observation_date"] for o in observations})
    return {
        "ok": bool(observations),
        "interval": interval,
        "from": start,
        "observations": observations,
        "count": len(observations),
        "days": len(days),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "failures": failures,
    }


def refresh(*, interval: str = "1D", since: Optional[str] = None,
            actor: str = "flow_refresh") -> dict[str, Any]:
    """Fetch and write. The route the engine already told people to call."""
    from market_intelligence_engine.ingest_flows import ingest_flows, normalise_upstox_flow

    pack = fetch(interval=interval, since=since)
    if not pack.get("ok"):
        # Named, because "no rows" and "the token is dead" need different
        # responses and the old failure looked identical to a quiet market.
        return {"ok": False, "error": "upstox_returned_no_observations",
                "failures": pack.get("failures"), "from": pack.get("from")}

    rows = normalise_upstox_flow({"observations": pack["observations"]})
    written = ingest_flows(rows, actor=actor)
    return {
        "ok": bool(written.get("ok", True)),
        "fetched": pack["count"],
        "days": pack["days"],
        "first_day": pack["first_day"],
        "last_day": pack["last_day"],
        "rows": len(rows),
        "written": written,
        "failures": pack.get("failures"),
    }
