"""AGI Sector Rotation V1 — Nifty sector index ranking, never a trading strategy.

IMPORTANT: strategy id must be agi_sector_rotation_v1 (not agi_sector_opportunity_v1).
Ingest expects payload.sectors[] with rotation in leading|improving|weakening|lagging.

Groww Cloud blocks outbound HTTPS. Production runs use Render:

  GROWW_SECTOR_ROTATION_SCHEDULER=true  (finance-news-backend on Render)

See server/services/growwSectorRotationRun.js

Groww Cloud vault env vars (never hardcode secrets in this file):
  GROWW_TOTP_TOKEN, GROWW_TOTP_SECRET
  RESEARCH_SIGNALS_INGEST_TOKEN, RESEARCH_SIGNALS_INGEST_SECRET  (delivery blocked from Groww Cloud)
"""
import hashlib
import hmac
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone

import pyotp
import requests
from growwapi import GrowwAPI

STRATEGY = "agi_sector_rotation_v1"
SCHEMA_VERSION = "1.0"
IST = timezone(timedelta(hours=5, minutes=30))

# Groww NSE sector index symbols. sector field in ingest = symbol (e.g. NIFTYBANK).
DEFAULT_SECTORS = (
    "NIFTYBANK,NIFTYIT,NIFTYAUTO,NIFTYFMCG,NIFTYPHARMA,NIFTYMETAL,NIFTYREALTY,"
    "NIFTYPSUBANK,FINNIFTY,NIFTYENERGY,NIFTYMEDIA"
)


def required_env(name, *, optional=False):
    value = os.getenv(name, "").strip()
    if not value and not optional:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def make_client():
    token = required_env("GROWW_TOTP_TOKEN")
    secret = required_env("GROWW_TOTP_SECRET")
    access_token = GrowwAPI.get_access_token(api_key=token, totp=pyotp.TOTP(secret).now())
    return GrowwAPI(access_token)


def unwrap(value):
    if isinstance(value, dict) and value.get("status") == "SUCCESS":
        return value.get("payload", {})
    return value or {}


def history(client, symbol, days=400):
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
    return [row for row in unwrap(raw).get("candles", []) if isinstance(row, (list, tuple)) and len(row) >= 6]


def return_pct(values, periods):
    if len(values) <= periods or not values[-periods - 1]:
        return None
    return ((values[-1] / values[-periods - 1]) - 1) * 100


def stdev(values):
    if len(values) < 2:
        return 0.0
    average = sum(values) / len(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / (len(values) - 1))


def clamp(value, low, high):
    return max(low, min(high, value))


def classify_rotation(rel20, rel60):
    if rel20 >= 0 and rel60 >= 0:
        return "leading"
    if rel20 >= 0 and rel60 < 0:
        return "improving"
    if rel20 < 0 and rel60 >= 0:
        return "weakening"
    return "lagging"


def analyse(sector, rows, benchmark):
    closes = [float(row[4]) for row in rows]
    if len(closes) < 125:
        return None

    r5 = return_pct(closes, 5)
    r20 = return_pct(closes, 20)
    r60 = return_pct(closes, 60)
    rel20 = (r20 or 0) - (benchmark.get("return_20d") or 0)
    rel60 = (r60 or 0) - (benchmark.get("return_60d") or 0)
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    ma100 = sum(closes[-100:]) / 100
    daily_returns = [((closes[i] / closes[i - 1]) - 1) * 100 for i in range(1, len(closes))]
    volatility = stdev(daily_returns[-20:]) * math.sqrt(252)
    high_60 = max(closes[-60:])
    drawdown_60 = ((closes[-1] / high_60) - 1) * 100
    peak_window = closes[-120:]
    max_drawdown = min(((closes[i] / max(peak_window[: i + 1])) - 1) * 100 for i in range(len(peak_window)))

    trend_points = 12 if closes[-1] > ma20 > ma50 > ma100 else 6 if closes[-1] > ma50 else -10
    score = round(
        clamp(
            50
            + clamp(rel20, -10, 10) * 1.1
            + clamp(rel60, -15, 15) * 0.8
            + trend_points
            - clamp(max(0, volatility - 18) * 0.45, 0, 10)
            + clamp(drawdown_60 + 10, -5, 5),
            0,
            100,
        ),
        1,
    )

    return {
        "sector": sector,
        "score": score,
        "close": round(closes[-1], 2),
        "return_5d": round(r5, 2) if r5 is not None else None,
        "return_20d": round(r20, 2) if r20 is not None else None,
        "return_60d": round(r60, 2) if r60 is not None else None,
        "relative_20d": round(rel20, 2),
        "relative_60d": round(rel60, 2),
        "volatility_20d": round(volatility, 2),
        "max_drawdown": round(max_drawdown, 2),
        "rotation": classify_rotation(rel20, rel60),
        "risk": "high" if volatility > 28 else "moderate" if volatility > 18 else "low",
        "factors": {
            "drawdown_60d": round(drawdown_60, 2),
            "trend": "positive" if closes[-1] > ma20 > ma50 > ma100 else "negative" if closes[-1] < ma20 < ma50 else "mixed",
        },
    }


def parse_sectors(raw):
    symbols = []
    for item in raw.split(","):
        entry = item.strip().upper()
        if not entry:
            continue
        if ":" in entry:
            _, symbol = entry.split(":", 1)
            symbols.append(symbol.strip().upper())
        else:
            symbols.append(entry)
    if not symbols:
        raise ValueError("AGI_SECTOR_UNIVERSE contains no sectors")
    return symbols


def deliver(payload):
    url = required_env(
        "AGI_INGEST_URL",
        optional=True,
    ) or "https://zrvdtpxfmuijhionbaxr.supabase.co/functions/v1/research-signals-ingest"
    token = required_env("RESEARCH_SIGNALS_INGEST_TOKEN")
    secret = required_env("RESEARCH_SIGNALS_INGEST_SECRET")
    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AGI-Groww-Sector-Rotation/1.0",
        "Authorization": f"Bearer {token}",
        "X-AGI-Signature": hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest(),
    }
    print(f"AGI delivering to: {url}")
    print("WARNING: Groww Cloud usually blocks outbound HTTPS — use Render scheduler instead.")
    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(url, data=body, headers=headers, timeout=45)
            print(
                json.dumps(
                    {
                        "delivered": response.ok,
                        "status": response.status_code,
                        "run_id": payload["run_id"],
                        "response": response.text[:500],
                    }
                )
            )
            if response.status_code in (200, 202):
                return
            if 400 <= response.status_code < 500 and response.status_code != 429:
                raise RuntimeError(f"AGI rejected ({response.status_code}): {response.text[:500]}")
            last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
        except Exception as error:
            last_error = error
        if attempt < 2:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"AGI delivery failed after 3 attempts: {last_error}")


def main():
    print("AGI sector rotation run starting")
    client = make_client()
    delay = max(0.0, float(os.getenv("AGI_CALL_DELAY_SEC", "0.25")))
    sectors = parse_sectors(os.getenv("AGI_SECTOR_UNIVERSE", DEFAULT_SECTORS))
    benchmark_symbol = os.getenv("AGI_BENCHMARK_SYMBOL", "NIFTY").strip().upper()

    nifty_rows = history(client, benchmark_symbol, days=400)
    nifty_closes = [float(row[4]) for row in nifty_rows]
    benchmark = {
        "symbol": benchmark_symbol,
        "return_20d": return_pct(nifty_closes, 20),
        "return_60d": return_pct(nifty_closes, 60),
    }
    if benchmark["return_20d"] is None or benchmark["return_60d"] is None:
        raise RuntimeError("Insufficient benchmark history")
    time.sleep(delay)

    results, errors = [], []
    for sector in sectors:
        try:
            result = analyse(sector, history(client, sector, days=400), benchmark)
            if result:
                results.append(result)
            else:
                errors.append({"sector": sector, "error": "Insufficient history"})
        except Exception as exc:
            errors.append({"sector": sector, "error": str(exc)[:180]})
        time.sleep(delay)

    results.sort(key=lambda row: row["score"], reverse=True)
    ranked = [{**row, "rank": rank} for rank, row in enumerate(results, 1)]
    now = datetime.now(IST)
    deliver(
        {
            "strategy": STRATEGY,
            "schema_version": SCHEMA_VERSION,
            "run_id": f"{STRATEGY}:{now.strftime('%Y%m%dT%H%M%S%z')}",
            "as_of": now.isoformat(),
            "research_only": True,
            "universe_size": len(sectors),
            "processed": len(results),
            "benchmark": benchmark,
            "sectors": ranked,
            "errors": errors[:20],
        }
    )


main()
