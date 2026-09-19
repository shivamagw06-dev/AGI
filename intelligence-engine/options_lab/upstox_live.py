"""Upstox-only live option-chain collection for Pricing Engine V1."""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time as clock_time, timedelta, timezone
from pathlib import Path
from typing import Any

from .engine import price_option_snapshot
from .store import OptionEvidenceStore
from .validation import create_validation_observations


IST = timezone(timedelta(hours=5, minutes=30))
API_BASE = "https://api.upstox.com/v2"
DEFAULT_UNDERLYING_KEY = "NSE_INDEX|Nifty 50"


class UpstoxLiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveConfig:
    database_path: Path
    report_directory: Path
    underlying_key: str = DEFAULT_UNDERLYING_KEY
    underlying_symbol: str = "NIFTY"
    strike_wings: int = 10
    max_expiries: int = 4
    max_dte_days: int = 30
    risk_free_rate_pct: float = 5.25
    max_validation_horizon_minutes: float = 30.0

    @classmethod
    def from_environment(cls) -> "LiveConfig":
        return cls(
            database_path=Path(
                os.getenv("OPTIONS_LAB_DB_PATH", "./data/options_lab.sqlite3")
            ),
            report_directory=Path(
                os.getenv("OPTIONS_LAB_REPORT_DIR", "./artifacts/options_lab")
            ),
            underlying_key=os.getenv(
                "OPTIONS_LAB_UNDERLYING_KEY", DEFAULT_UNDERLYING_KEY
            ),
            underlying_symbol=os.getenv("OPTIONS_LAB_UNDERLYING_SYMBOL", "NIFTY"),
            strike_wings=int(os.getenv("OPTIONS_LAB_STRIKE_WINGS", "10")),
            max_expiries=int(os.getenv("OPTIONS_LAB_MAX_EXPIRIES", "4")),
            max_dte_days=int(os.getenv("OPTIONS_LAB_MAX_DTE_DAYS", "30")),
            risk_free_rate_pct=float(
                os.getenv("OPTIONS_LAB_RISK_FREE_RATE_PCT", "5.25")
            ),
            max_validation_horizon_minutes=float(
                os.getenv("OPTIONS_LAB_MAX_VALIDATION_HORIZON_MINUTES", "30")
            ),
        )


def load_access_token() -> str:
    token_file = os.getenv("UPSTOX_ACCESS_TOKEN_FILE")
    if token_file:
        token = Path(token_file).expanduser().read_text(encoding="utf-8").strip()
    else:
        token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        raise UpstoxLiveError(
            "UPSTOX_ACCESS_TOKEN or UPSTOX_ACCESS_TOKEN_FILE is required"
        )
    return token


class UpstoxClient:
    def __init__(self, token: str, *, timeout_seconds: int = 25):
        self._token = token
        self._timeout = timeout_seconds

    def _get(self, path: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode(parameters)
        request = urllib.request.Request(
            f"{API_BASE}{path}?{query}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "AGI-Pricing-Engine-V1/1.0",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") != "success":
                    raise UpstoxLiveError(
                        f"Upstox returned status={payload.get('status')!r}"
                    )
                data = payload.get("data")
                if not isinstance(data, list):
                    raise UpstoxLiveError("Upstox response data is not a list")
                return data
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")[:500]
                if error.code in (401, 403):
                    raise UpstoxLiveError(
                        "Upstox authorization failed; rotate the access token"
                    ) from error
                if error.code != 429 and error.code < 500:
                    raise UpstoxLiveError(
                        f"Upstox HTTP {error.code}: {body}"
                    ) from error
                if attempt == 2:
                    raise UpstoxLiveError(
                        f"Upstox HTTP {error.code} after retries: {body}"
                    ) from error
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == 2:
                    raise UpstoxLiveError(
                        f"Upstox request failed after retries: {error}"
                    ) from error
            time.sleep(2**attempt)
        raise UpstoxLiveError("unreachable Upstox retry state")

    def option_contracts(self, underlying_key: str) -> list[dict[str, Any]]:
        return self._get("/option/contract", {"instrument_key": underlying_key})

    def option_chain(
        self, underlying_key: str, expiry_date: str
    ) -> list[dict[str, Any]]:
        return self._get(
            "/option/chain",
            {"instrument_key": underlying_key, "expiry_date": expiry_date},
        )


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _market_price(market: dict[str, Any]) -> tuple[float | None, str]:
    bid = _number(market.get("bid_price"))
    ask = _number(market.get("ask_price"))
    if bid is not None and ask is not None and bid > 0 and ask >= bid:
        return (bid + ask) / 2.0, "bid_ask_mid"
    ltp = _number(market.get("ltp"))
    return (ltp, "ltp") if ltp is not None and ltp > 0 else (None, "missing")


def _expiry_dte(expiry: date, captured_at: datetime) -> float:
    expiry_at = datetime.combine(expiry, clock_time(15, 30), tzinfo=IST)
    return max((expiry_at - captured_at.astimezone(IST)).total_seconds() / 86400, 1e-6)


def _normalize_provider_iv(value: Any) -> float | None:
    iv = _number(value)
    if iv is None or iv <= 0:
        return None
    if iv <= 3:
        iv *= 100.0
    return iv if iv <= 500 else None


def _solve_iv(
    *,
    spot: float,
    strike: float,
    dte_days: float,
    option_type: str,
    risk_free_rate_pct: float,
    dividend_yield_pct: float,
    market_price: float,
) -> float | None:
    try:
        result = price_option_snapshot(
            {
                "spot": spot,
                "strike": strike,
                "days_to_expiry": dte_days,
                "risk_free_rate_pct": risk_free_rate_pct,
                "dividend_yield_pct": dividend_yield_pct,
                "option_type": "call" if option_type == "CE" else "put",
                "model_volatility_pct": 20.0,
                "bid": market_price,
                "ask": market_price,
            }
        )
    except (TypeError, ValueError):
        return None
    value = (result.get("implied_volatility") or {}).get("mid_pct")
    return _normalize_provider_iv(value)


def _parity_yield(
    chain: list[dict[str, Any]],
    *,
    spot: float,
    expiry: date,
    captured_at: datetime,
    risk_free_rate_pct: float,
) -> float:
    if not chain:
        return 0.0
    atm = min(chain, key=lambda row: abs(float(row.get("strike_price") or 0) - spot))
    call_price, _ = _market_price(
        (atm.get("call_options") or {}).get("market_data") or {}
    )
    put_price, _ = _market_price(
        (atm.get("put_options") or {}).get("market_data") or {}
    )
    strike = _number(atm.get("strike_price"))
    if call_price is None or put_price is None or strike is None:
        return 0.0
    years = _expiry_dte(expiry, captured_at) / 365.0
    discounted_spot = (
        call_price
        - put_price
        + strike * math.exp(-(risk_free_rate_pct / 100.0) * years)
    )
    if discounted_spot <= 0 or spot <= 0:
        return 0.0
    raw = -math.log(discounted_spot / spot) / years * 100.0
    return raw if math.isfinite(raw) and 0 <= raw <= 20 else 0.0


def _eligible_expiries(
    contracts: list[dict[str, Any]], config: LiveConfig, today: date
) -> list[str]:
    maximum = today + timedelta(days=config.max_dte_days)
    expiries = sorted(
        {
            str(row.get("expiry"))
            for row in contracts
            if row.get("expiry")
            and today <= date.fromisoformat(str(row["expiry"])) <= maximum
        }
    )
    return expiries[: config.max_expiries]


def _rows_for_chain(
    chain: list[dict[str, Any]],
    contracts_by_key: dict[str, dict[str, Any]],
    *,
    expiry_text: str,
    captured_at: datetime,
    config: LiveConfig,
) -> list[dict[str, Any]]:
    spot_values = [
        _number(row.get("underlying_spot_price"))
        for row in chain
        if _number(row.get("underlying_spot_price")) is not None
    ]
    if not spot_values:
        raise UpstoxLiveError(f"option chain {expiry_text} has no underlying spot")
    spot = spot_values[0]
    expiry = date.fromisoformat(expiry_text)
    ranked = sorted(
        chain,
        key=lambda row: abs(float(row.get("strike_price") or 0) - spot),
    )
    selected_strikes = {
        float(row["strike_price"]) for row in ranked[: 1 + config.strike_wings * 2]
    }
    selected = [
        row for row in chain if float(row.get("strike_price") or 0) in selected_strikes
    ]
    dividend_yield_pct = _parity_yield(
        selected,
        spot=spot,
        expiry=expiry,
        captured_at=captured_at,
        risk_free_rate_pct=config.risk_free_rate_pct,
    )
    dte_days = _expiry_dte(expiry, captured_at)
    normalized: list[dict[str, Any]] = []
    for pair in selected:
        strike = float(pair["strike_price"])
        for option_type, key in (("CE", "call_options"), ("PE", "put_options")):
            option = pair.get(key) or {}
            instrument_key = str(option.get("instrument_key") or "")
            market = option.get("market_data") or {}
            greeks = option.get("option_greeks") or {}
            market_price, price_source = _market_price(market)
            if not instrument_key or market_price is None:
                continue
            iv_pct = _normalize_provider_iv(greeks.get("iv"))
            iv_source = "upstox"
            if iv_pct is None:
                iv_pct = _solve_iv(
                    spot=spot,
                    strike=strike,
                    dte_days=dte_days,
                    option_type=option_type,
                    risk_free_rate_pct=config.risk_free_rate_pct,
                    dividend_yield_pct=dividend_yield_pct,
                    market_price=market_price,
                )
                iv_source = "pricing_engine_v1" if iv_pct is not None else "missing"
            metadata = contracts_by_key.get(instrument_key, {})
            normalized.append(
                {
                    "captured_at": captured_at.astimezone(timezone.utc).isoformat(),
                    "local_date": captured_at.astimezone(IST).date().isoformat(),
                    "provider": "upstox",
                    "underlying_key": config.underlying_key,
                    "underlying_symbol": config.underlying_symbol,
                    "spot": spot,
                    "expiry": expiry_text,
                    "instrument_key": instrument_key,
                    "trading_symbol": metadata.get("trading_symbol"),
                    "option_type": option_type,
                    "strike": strike,
                    "lot_size": metadata.get("lot_size"),
                    "dte_days": dte_days,
                    "risk_free_rate_pct": config.risk_free_rate_pct,
                    "dividend_yield_pct": dividend_yield_pct,
                    "ltp": _number(market.get("ltp")),
                    "bid": _number(market.get("bid_price")),
                    "ask": _number(market.get("ask_price")),
                    "market_price": market_price,
                    "close_price": _number(market.get("close_price")),
                    "volume": _number(market.get("volume")),
                    "oi": _number(market.get("oi")),
                    "prev_oi": _number(market.get("prev_oi")),
                    "iv_pct": iv_pct,
                    "iv_source": f"{iv_source}:{price_source}",
                    "delta": _number(greeks.get("delta")),
                    "gamma": _number(greeks.get("gamma")),
                    "theta": _number(greeks.get("theta")),
                    "vega": _number(greeks.get("vega")),
                    "rho": _number(greeks.get("rho")),
                    "pop": _number(greeks.get("pop")),
                    "raw_json": json.dumps(
                        {"market_data": market, "option_greeks": greeks},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                }
            )
    return normalized


def collect_once(
    config: LiveConfig | None = None,
    *,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    config = config or LiveConfig.from_environment()
    captured_at = captured_at or datetime.now(timezone.utc)
    client = UpstoxClient(load_access_token())
    store = OptionEvidenceStore(config.database_path)
    contracts = client.option_contracts(config.underlying_key)
    contracts_by_key = {
        str(row["instrument_key"]): row for row in contracts if row.get("instrument_key")
    }
    expiries = _eligible_expiries(
        contracts, config, captured_at.astimezone(IST).date()
    )
    if not expiries:
        raise UpstoxLiveError("no eligible NIFTY expiries in the next 30 days")
    run_id = str(uuid.uuid4())
    store.start_run(run_id, captured_at.isoformat(), expiries)
    counts: dict[str, Any] = {
        "expiries": len(expiries),
        "received_rows": 0,
        "inserted_snapshots": 0,
        "validation_observations": 0,
    }
    try:
        rows: list[dict[str, Any]] = []
        for expiry in expiries:
            rows.extend(
                _rows_for_chain(
                    client.option_chain(config.underlying_key, expiry),
                    contracts_by_key,
                    expiry_text=expiry,
                    captured_at=captured_at,
                    config=config,
                )
            )
        counts["received_rows"] = len(rows)
        inserted = store.persist_snapshots(rows)
        counts["inserted_snapshots"] = len(inserted)
        counts["validation_observations"] = create_validation_observations(
            store,
            inserted,
            max_horizon_minutes=config.max_validation_horizon_minutes,
        )
        store.finish_run(
            run_id, datetime.now(timezone.utc).isoformat(), "success", counts
        )
        return {"run_id": run_id, "status": "success", **counts}
    except Exception as error:
        store.finish_run(
            run_id,
            datetime.now(timezone.utc).isoformat(),
            "failed",
            counts,
            str(error)[:1000],
        )
        raise
