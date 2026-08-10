"""AGI Equity Opportunity V1 — research shortlist, never a trading strategy.

Groww Cloud can fetch market data but blocks ALL outbound HTTPS (Render and
Supabase both time out). Use the Render scheduler instead:

  GROWW_EQUITY_OPPORTUNITY_SCHEDULER=true

See server/services/growwEquityOpportunityRun.js
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

# Deprecated on Groww Cloud — kept for reference / manual runs from Render shell.
AGI_INGEST_URL = os.getenv(
    "AGI_INGEST_URL",
    "https://zrvdtpxfmuijhionbaxr.supabase.co/functions/v1/research-signals-ingest",
)
AGI_INGEST_TOKEN = os.getenv("RESEARCH_SIGNALS_INGEST_TOKEN", "PASTE_RESEARCH_SIGNALS_INGEST_TOKEN")
AGI_INGEST_SECRET = os.getenv("RESEARCH_SIGNALS_INGEST_SECRET", "PASTE_RESEARCH_SIGNALS_INGEST_SECRET")
GROWW_TOTP_TOKEN = "PASTE_GROWW_TOTP_TOKEN"
GROWW_TOTP_SECRET = "PASTE_GROWW_TOTP_SECRET"

TRADING_ENABLED = False
STRATEGY = "agi_equity_opportunity_v1"
SCHEMA_VERSION = "1.0"
IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_UNIVERSE = "RELIANCE,HDFCBANK,ICICIBANK,INFY,TCS,BHARTIARTL,ITC,LT,SBIN,AXISBANK,KOTAKBANK,HINDUNILVR,BAJFINANCE,MARUTI,SUNPHARMA,NTPC,TITAN,ULTRACEMCO,ASIANPAINT,POWERGRID,M&M,NESTLEIND,TATASTEEL,ONGC,TECHM,WIPRO,COALINDIA,JSWSTEEL,HCLTECH,ADANIENT,ADANIPORTS,BAJAJFINSV,GRASIM,DRREDDY,CIPLA,EICHERMOT,HEROMOTOCO,APOLLOHOSP,BRITANNIA,DIVISLAB,INDUSINDBK,TATACONSUM,SBILIFE,HDFCLIFE,BPCL,SHRIRAMFIN,TRENT,BEL,JIOFIN,BAJAJ-AUTO"


def make_client():
    if GROWW_TOTP_TOKEN.startswith("PASTE_") or GROWW_TOTP_SECRET.startswith("PASTE_"):
        raise RuntimeError("Paste Groww TOTP token + secret at the top of the strategy.")
    return GrowwAPI(GrowwAPI.get_access_token(api_key=GROWW_TOTP_TOKEN.strip(), totp=pyotp.TOTP(GROWW_TOTP_SECRET.strip()).now()))


def unwrap(value):
    return value.get("payload", value) if isinstance(value, dict) and value.get("status") == "SUCCESS" else value or {}


def history(client, symbol, days=175):
    instrument = client.get_instrument_by_exchange_and_trading_symbol(exchange=client.EXCHANGE_NSE, trading_symbol=symbol)
    if not isinstance(instrument, dict):
        raise ValueError(f"Instrument not found: {symbol}")
    end = datetime.now(IST)
    start = end - timedelta(days=days)
    raw = client.get_historical_candles(
        exchange=instrument["exchange"], segment=instrument["segment"], groww_symbol=instrument["groww_symbol"],
        start_time=start.strftime("%Y-%m-%d %H:%M:%S"), end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
        candle_interval=client.CANDLE_INTERVAL_DAY,
    )
    return [r for r in unwrap(raw).get("candles", []) if isinstance(r, (list, tuple)) and len(r) >= 6]


def return_pct(values, n):
    return ((values[-1] / values[-n - 1]) - 1) * 100 if len(values) > n and values[-n - 1] else None


def stdev(values):
    if len(values) < 2:
        return 0
    avg = sum(values) / len(values)
    return math.sqrt(sum((v - avg) ** 2 for v in values) / (len(values) - 1))


def analyse(symbol, rows, benchmark):
    closes = [float(r[4]) for r in rows]
    volumes = [float(r[5]) for r in rows]
    if len(closes) < 65:
        return None
    r20, r60 = return_pct(closes, 20), return_pct(closes, 60)
    daily = [((closes[i] / closes[i - 1]) - 1) * 100 for i in range(1, len(closes))]
    vol = stdev(daily[-20:]) * math.sqrt(252)
    volume_avg = sum(volumes[-20:]) / 20
    volume_ratio = volumes[-1] / volume_avg if volume_avg else 0
    ma20, ma50 = sum(closes[-20:]) / 20, sum(closes[-50:]) / 50
    relative20 = (r20 or 0) - (benchmark.get("return_20d") or 0)
    relative60 = (r60 or 0) - (benchmark.get("return_60d") or 0)
    score = round(max(0, min(100, 50 + max(-15, min(15, r20 or 0)) + max(-15, min(15, relative60)) + (8 if closes[-1] > ma20 > ma50 else -8) + (5 if volume_ratio > 1.2 else 0) - max(0, min(10, (vol - 20) / 2)))), 1)
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
    return {
        "symbol": symbol, "score": score, "close": closes[-1],
        "return_20d": round(r20, 2) if r20 is not None else None,
        "return_60d": round(r60, 2) if r60 is not None else None,
        "relative_20d": round(relative20, 2), "relative_60d": round(relative60, 2),
        "volatility_20d": round(vol, 2), "volume_ratio": round(volume_ratio, 2),
        "trend": "positive" if closes[-1] > ma20 > ma50 else "negative" if closes[-1] < ma20 < ma50 else "mixed",
        "volume_confirmation": volume_ratio > 1.2,
        "risk": "high" if vol > 30 else "moderate" if vol > 20 else "low",
        "reasons": reasons or ["No strong factor confirmation"],
    }


def deliver(payload):
    if AGI_INGEST_TOKEN.startswith("PASTE_") or AGI_INGEST_SECRET.startswith("PASTE_"):
        raise RuntimeError("Configure AGI_INGEST_TOKEN and AGI_INGEST_SECRET.")
    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AGI-Groww-Research/1.0",
        "Authorization": f"Bearer {AGI_INGEST_TOKEN.strip()}",
        "X-AGI-Signature": hmac.new(AGI_INGEST_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest(),
    }
    print(f"AGI delivering to: {AGI_INGEST_URL}")
    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(AGI_INGEST_URL, data=body, headers=headers, timeout=45)
            print(json.dumps({"delivered": response.ok, "status": response.status_code, "run_id": payload["run_id"], "response": response.text[:500]}))
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
    print("AGI equity opportunity run starting")
    client = make_client()
    delay = float(os.getenv("AGI_CALL_DELAY_SEC", "0.22"))
    limit = max(5, min(200, int(os.getenv("AGI_MAX_SYMBOLS", "10"))))
    symbols = [s.strip().upper() for s in os.getenv("AGI_UNIVERSE", DEFAULT_UNIVERSE).split(",") if s.strip()][:limit]
    nifty = history(client, "NIFTY", days=175)
    nclose = [float(r[4]) for r in nifty]
    benchmark = {"return_20d": return_pct(nclose, 20), "return_60d": return_pct(nclose, 60)}
    time.sleep(delay)
    rows, errors = [], []
    for symbol in symbols:
        try:
            result = analyse(symbol, history(client, symbol, days=175), benchmark)
            if result:
                rows.append(result)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": str(exc)[:160]})
        time.sleep(delay)
    rows.sort(key=lambda row: row["score"], reverse=True)
    candidates = [{**row, "rank": i + 1, "signal": "research_candidate"} for i, row in enumerate(rows[:10])]
    deteriorating = [{**row, "signal": "risk_review"} for row in sorted(rows, key=lambda r: r["score"])[:10]]
    now = datetime.now(IST)
    deliver({
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
    })


main()
