"""AGI Equity Opportunity V1 — research shortlist, never a trading strategy.

Runs on Groww Cloud. Computes a ranked equity shortlist from Groww historical
candles and delivers a signed payload to the AGI Node ingest endpoint.

Configure secrets in Groww Cloud strategy settings (never commit real values):
  AGI_INGEST_TOKEN  -> Render RESEARCH_SIGNALS_INGEST_TOKEN
  AGI_INGEST_SECRET -> Render RESEARCH_SIGNALS_INGEST_SECRET
  GROWW_TOTP_TOKEN / GROWW_TOTP_SECRET -> Groww Cloud > Keys > TOTP
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import pyotp
from growwapi import GrowwAPI

# ---------------------------------------------------------------------------
# Private delivery configuration (paste in Groww Cloud strategy editor only)
# ---------------------------------------------------------------------------
AGI_INGEST_URL = os.getenv(
    "AGI_INGEST_URL",
    "https://finance-news-backend-19i5.onrender.com/api/research-signals/ingest",
).strip()
AGI_HEALTH_URL = os.getenv(
    "AGI_HEALTH_URL",
    "https://finance-news-backend-19i5.onrender.com/api/health",
).strip()
AGI_INGEST_TOKEN = os.getenv("AGI_INGEST_TOKEN", "PASTE_RESEARCH_SIGNALS_INGEST_TOKEN").strip()
AGI_INGEST_SECRET = os.getenv("AGI_INGEST_SECRET", "PASTE_RESEARCH_SIGNALS_INGEST_SECRET").strip()

GROWW_TOTP_TOKEN = os.getenv("GROWW_TOTP_TOKEN", "PASTE_GROWW_TOTP_TOKEN").strip()
GROWW_TOTP_SECRET = os.getenv("GROWW_TOTP_SECRET", "PASTE_GROWW_TOTP_SECRET").strip()

TRADING_ENABLED = False
STRATEGY = "agi_equity_opportunity_v1"
SCHEMA_VERSION = "1.0"
IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_UNIVERSE = (
    "RELIANCE,HDFCBANK,ICICIBANK,INFY,TCS,BHARTIARTL,ITC,LT,SBIN,AXISBANK,"
    "KOTAKBANK,HINDUNILVR,BAJFINANCE,MARUTI,SUNPHARMA,NTPC,TITAN,ULTRACEMCO,"
    "ASIANPAINT,POWERGRID,M&M,NESTLEIND,TATASTEEL,ONGC,TECHM,WIPRO,COALINDIA,"
    "JSWSTEEL,HCLTECH,ADANIENT,ADANIPORTS,BAJAJFINSV,GRASIM,DRREDDY,CIPLA,"
    "EICHERMOT,HEROMOTOCO,APOLLOHOSP,BRITANNIA,DIVISLAB,INDUSINDBK,TATACONSUM,"
    "SBILIFE,HDFCLIFE,BPCL,SHRIRAMFIN,TRENT,BEL,JIOFIN,BAJAJ-AUTO"
)


def make_client() -> GrowwAPI:
    if GROWW_TOTP_TOKEN.startswith("PASTE_") or GROWW_TOTP_SECRET.startswith("PASTE_"):
        raise RuntimeError(
            "Paste your Groww TOTP token and TOTP secret into the placeholders "
            "at the top of the strategy (or set GROWW_TOTP_TOKEN / GROWW_TOTP_SECRET)."
        )
    access_token = GrowwAPI.get_access_token(
        api_key=GROWW_TOTP_TOKEN,
        totp=pyotp.TOTP(GROWW_TOTP_SECRET).now(),
    )
    return GrowwAPI(access_token)


def unwrap(value):
    if isinstance(value, dict) and value.get("status") == "SUCCESS":
        return value.get("payload", value)
    return value or {}


def history(client: GrowwAPI, symbol: str, days: int = 175):
    instrument = client.get_instrument_by_exchange_and_trading_symbol(
        exchange=client.EXCHANGE_NSE,
        trading_symbol=symbol,
    )
    if not isinstance(instrument, dict):
        raise ValueError(f"Instrument not found: {symbol}")
    end = datetime.now(IST)
    start = end - timedelta(days=days)
    raw = client.get_historical_candles(
        exchange=instrument["exchange"],
        segment=instrument["segment"],
        groww_symbol=instrument["groww_symbol"],
        start_time=start.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
        candle_interval=client.CANDLE_INTERVAL_DAY,
    )
    return [
        row
        for row in unwrap(raw).get("candles", [])
        if isinstance(row, (list, tuple)) and len(row) >= 6
    ]


def return_pct(values, n: int):
    if len(values) > n and values[-n - 1]:
        return ((values[-1] / values[-n - 1]) - 1) * 100
    return None


def stdev(values):
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return math.sqrt(sum((v - avg) ** 2 for v in values) / (len(values) - 1))


def analyse(symbol: str, rows, benchmark: dict):
    closes = [float(row[4]) for row in rows]
    volumes = [float(row[5]) for row in rows]
    if len(closes) < 65:
        return None

    r20 = return_pct(closes, 20)
    r60 = return_pct(closes, 60)
    daily = [((closes[i] / closes[i - 1]) - 1) * 100 for i in range(1, len(closes))]
    vol = stdev(daily[-20:]) * math.sqrt(252)
    volume_avg = sum(volumes[-20:]) / 20
    volume_ratio = volumes[-1] / volume_avg if volume_avg else 0
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    relative20 = (r20 or 0) - (benchmark.get("return_20d") or 0)
    relative60 = (r60 or 0) - (benchmark.get("return_60d") or 0)

    score = (
        50
        + max(-15, min(15, r20 or 0))
        + max(-15, min(15, relative60))
        + (8 if closes[-1] > ma20 > ma50 else -8)
        + (5 if volume_ratio > 1.2 else 0)
        - max(0, min(10, (vol - 20) / 2))
    )
    score = round(max(0, min(100, score)), 1)

    reasons = []
    if closes[-1] > ma20 > ma50:
        reasons.append("Price above rising 20/50-day structure")
    if relative20 > 3:
        reasons.append("Twenty-day outperformance versus Nifty")
    if relative60 > 5:
        reasons.append("Persistent sixty-day relative strength")
    if volume_ratio > 1.2:
        reasons.append("Latest volume above twenty-day average")
    if vol > 30:
        reasons.append("Elevated volatility requires risk review")

    trend = (
        "positive"
        if closes[-1] > ma20 > ma50
        else "negative"
        if closes[-1] < ma20 < ma50
        else "mixed"
    )
    risk = "high" if vol > 30 else "moderate" if vol > 20 else "low"

    return {
        "symbol": symbol,
        "score": score,
        "close": closes[-1],
        "return_20d": round(r20, 2) if r20 is not None else None,
        "return_60d": round(r60, 2) if r60 is not None else None,
        "relative_20d": round(relative20, 2),
        "relative_60d": round(relative60, 2),
        "volatility_20d": round(vol, 2),
        "volume_ratio": round(volume_ratio, 2),
        "trend": trend,
        "volume_confirmation": volume_ratio > 1.2,
        "risk": risk,
        "reasons": reasons or ["No strong factor confirmation"],
    }


def wake_node_api(timeout_seconds: float = 15.0) -> None:
    """Best-effort wake for Render cold start. Never blocks delivery."""
    if not AGI_HEALTH_URL:
        return
    try:
        with urllib.request.urlopen(AGI_HEALTH_URL, timeout=timeout_seconds) as response:
            print(f"AGI API wake-up status: {response.status}")
    except Exception as error:
        print(f"AGI API wake-up warning: {str(error)[:200]}")


def deliver(payload: dict) -> None:
    """Deliver a signed research result to the AGI Node API."""
    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")

    url = AGI_INGEST_URL.strip()
    ingest_token = AGI_INGEST_TOKEN.strip()
    ingest_secret = AGI_INGEST_SECRET.strip()

    if (
        not url
        or not ingest_token
        or not ingest_secret
        or ingest_token.startswith("PASTE_")
        or ingest_secret.startswith("PASTE_")
    ):
        raise RuntimeError(
            "Configure AGI_INGEST_URL, AGI_INGEST_TOKEN and AGI_INGEST_SECRET "
            "at the top of the private Groww strategy."
        )

    wake_node_api(timeout_seconds=15.0)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AGI-Groww-Research/1.0",
        "Authorization": f"Bearer {ingest_token}",
        "X-AGI-Signature": hmac.new(
            ingest_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest(),
    }

    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=60) as response:
                response_text = response.read().decode("utf-8", errors="replace")
                print(
                    json.dumps(
                        {
                            "delivered": True,
                            "status": response.status,
                            "run_id": payload["run_id"],
                            "response": response_text[:500],
                        }
                    )
                )
                return
        except urllib.error.HTTPError as error:
            response_text = error.read().decode("utf-8", errors="replace")
            if 400 <= error.code < 500 and error.code != 429:
                raise RuntimeError(
                    f"AGI rejected the strategy result ({error.code}): {response_text[:500]}"
                ) from error
            last_error = RuntimeError(f"AGI ingestion HTTP {error.code}: {response_text[:500]}")
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error

        if attempt < 2:
            wait_seconds = 5 * (attempt + 1)
            print(f"AGI delivery attempt {attempt + 1} failed. Retrying in {wait_seconds} seconds.")
            time.sleep(wait_seconds)

    raise RuntimeError(f"AGI result delivery failed after three attempts: {last_error}")


def main():
    if TRADING_ENABLED:
        raise RuntimeError("This strategy is research-only. TRADING_ENABLED must stay False.")

    client = make_client()
    delay = float(os.getenv("AGI_CALL_DELAY_SEC", "0.22"))
    limit = max(10, min(200, int(os.getenv("AGI_MAX_SYMBOLS", "75"))))
    symbols = [
        symbol.strip().upper()
        for symbol in os.getenv("AGI_UNIVERSE", DEFAULT_UNIVERSE).split(",")
        if symbol.strip()
    ][:limit]

    nifty = history(client, "NIFTY", days=175)
    nclose = [float(row[4]) for row in nifty]
    benchmark = {
        "return_20d": return_pct(nclose, 20),
        "return_60d": return_pct(nclose, 60),
    }

    time.sleep(delay)
    rows = []
    errors = []
    for symbol in symbols:
        try:
            result = analyse(symbol, history(client, symbol, days=175), benchmark)
            if result:
                rows.append(result)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": str(exc)[:160]})
        time.sleep(delay)

    rows.sort(key=lambda row: row["score"], reverse=True)
    candidates = [
        {**row, "rank": index + 1, "signal": "research_candidate"}
        for index, row in enumerate(rows[:10])
    ]
    deteriorating = [
        {**row, "signal": "risk_review"}
        for row in sorted(rows, key=lambda item: item["score"])[:10]
    ]

    now = datetime.now(IST)
    payload = {
        "strategy": STRATEGY,
        "schema_version": SCHEMA_VERSION,
        "run_id": f"{STRATEGY}:{now.strftime('%Y%m%dT%H%M%S%z')}",
        "as_of": now.isoformat(),
        "research_only": True,
        "universe_size": len(symbols),
        "processed": len(rows),
        "benchmark": benchmark,
        "candidates": candidates,
        "deteriorating": deteriorating,
        "errors": errors[:20],
    }
    deliver(payload)


if __name__ == "__main__":
    main()
