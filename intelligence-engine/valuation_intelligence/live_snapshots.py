"""PIT-safe live valuation state and material permanent snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Callable


CALCULATION_VERSION = "pit_valuation_v1.0.0"
SNAPSHOT_INTERVAL_MINUTES = 15
MATERIAL_PRICE_MOVE_PCT = 1.0
EVENT_REASONS = {"MARKET_OPEN", "MIDDAY", "DAILY_CLOSE", "FINANCIAL_EVENT", "CORPORATE_ACTION"}

ALIASES = {
    "shares_outstanding": ("shares_outstanding_million", "shares_outstanding", "weighted_average_shares"),
    "eps": ("diluted_eps", "basic_eps", "eps"),
    "book_value_per_share": ("book_value_per_share", "bvps"),
    "tangible_book_value_per_share": ("tangible_book_value_per_share", "tbvps"),
    "ebitda": ("ebitda",), "revenue": ("revenue", "total_revenue", "sales"),
    "free_cash_flow": ("free_cash_flow", "fcf"), "debt": ("total_debt", "debt"),
    "cash": ("cash_and_equivalents", "cash"), "equity": ("total_equity", "shareholders_equity", "equity"),
    "tangible_book_value": ("tangible_book_value",), "roe": ("roe",), "roa": ("roa",),
}


def _number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and abs(out) != float("inf") else None


def _ratio(numerator: float | None, denominator: float | None, *, percent: bool = False) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    value = numerator / denominator * (100.0 if percent else 1.0)
    return round(value, 4)


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value or "").strip()
    return text or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _period_end(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return text[:10]
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) >= 4:
        year = int(digits[-4:])
        return f"{year:04d}-03-31"
    if len(digits) == 2:
        return f"20{digits}-03-31"
    return None


def build_fundamental_vintage(facts: list[dict[str, Any]], *, price_as_of: str) -> dict[str, Any]:
    """Select the latest eligible, already-public fact for each denominator."""
    cutoff = price_as_of[:10]
    selected: dict[str, dict[str, Any]] = {}
    for canonical, aliases in ALIASES.items():
        candidates = []
        for fact in facts:
            metric = str(fact.get("canonical_metric") or fact.get("metric") or "").lower()
            if metric not in aliases:
                continue
            publication = str(fact.get("available_at") or fact.get("publication_date") or "")
            if not publication or publication[:10] > cutoff:
                continue
            value = _number(fact.get("normalized_value", fact.get("value")))
            if value is None:
                continue
            period_end = _period_end(fact.get("period_end") or fact.get("reporting_period")) or ""
            candidates.append((period_end, publication, fact, value))
        if candidates:
            _, _, fact, value = sorted(candidates, key=lambda row: (row[0], row[1]))[-1]
            selected[canonical] = {"value": value, "fact": fact}
    publications = [str(item["fact"].get("available_at") or item["fact"].get("publication_date")) for item in selected.values()]
    periods = [str(item["fact"].get("period_end") or item["fact"].get("reporting_period")) for item in selected.values()]
    source_ids = sorted(str(item["fact"].get("source_id") or item["fact"].get("fact_id") or "") for item in selected.values())
    vintage_id = hashlib.sha256("|".join(source_ids).encode()).hexdigest()[:24] if source_ids else ""
    return {
        "values": {key: item["value"] for key, item in selected.items()},
        "fundamental_as_of": max(periods) if periods else None,
        "fundamental_publication_date": max(publications) if publications else None,
        "fundamental_vintage_id": vintage_id,
        "source_ids": source_ids,
        "source": "validated_warehouse",
    }


def calculate_state(*, quote: dict[str, Any], vintage: dict[str, Any], calculated_at: str | None = None) -> dict[str, Any]:
    symbol = str(quote.get("symbol") or "").upper()
    price = _number(quote.get("last", quote.get("price")))
    raw_price_as_of = quote.get("price_as_of") or quote.get("vendor_as_of") or quote.get("pulled_at")
    price_as_of = _iso(raw_price_as_of) if raw_price_as_of else ""
    publication = str(vintage.get("fundamental_publication_date") or "")
    fundamental_as_of = str(vintage.get("fundamental_as_of") or "")
    vintage_id = str(vintage.get("fundamental_vintage_id") or "")
    missing_pit = [name for name, value in {
        "price_as_of": price_as_of, "fundamental_as_of": fundamental_as_of,
        "fundamental_publication_date": publication, "fundamental_vintage_id": vintage_id,
    }.items() if not value]
    if not symbol or price is None or price <= 0 or missing_pit:
        return {"ok": False, "status": "DATA_REQUIRED",
                "missing": (["symbol_or_price"] if not symbol or price is None or price <= 0 else []) + missing_pit}
    if publication[:10] > price_as_of[:10]:
        return {"ok": False, "status": "PIT_INVALID", "price_as_of": price_as_of,
                "fundamental_publication_date": publication or None}
    values = vintage.get("values") or {}
    shares = _number(values.get("shares_outstanding"))
    shares_million = shares / 1_000_000.0 if shares is not None and shares > 100_000 else shares
    market_cap = _number(quote.get("market_cap"))
    if market_cap is None and shares_million is not None:
        market_cap = price * shares_million
    debt, cash = _number(values.get("debt")), _number(values.get("cash"))
    enterprise_value = market_cap + (debt or 0) - (cash or 0) if market_cap is not None else None
    eps = _number(values.get("eps"))
    bvps, tbvps = _number(values.get("book_value_per_share")), _number(values.get("tangible_book_value_per_share"))
    if bvps is None and shares_million:
        bvps = _ratio(_number(values.get("equity")), shares_million)
    if tbvps is None and shares_million:
        tbvps = _ratio(_number(values.get("tangible_book_value")), shares_million)
    ebitda, revenue, fcf = _number(values.get("ebitda")), _number(values.get("revenue")), _number(values.get("free_cash_flow"))
    missing = [name for name, value in {
        "shares_or_market_cap": market_cap, "eps": eps, "book_value_per_share": bvps,
        "ebitda": ebitda, "revenue": revenue,
    }.items() if value is None]
    row = {
        "symbol": symbol, "price": round(price, 4), "volume": _number(quote.get("volume")),
        "market_cap": round(market_cap, 4) if market_cap is not None else None,
        "enterprise_value": round(enterprise_value, 4) if enterprise_value is not None else None,
        "pe": _ratio(price, eps), "pb": _ratio(price, bvps), "ptbv": _ratio(price, tbvps),
        "ev_ebitda": _ratio(enterprise_value, ebitda), "ev_sales": _ratio(enterprise_value, revenue),
        "fcf_yield": _ratio(fcf, market_cap, percent=True),
        "net_debt_ebitda": _ratio((debt or 0) - (cash or 0), ebitda),
        "roe": _number(values.get("roe")), "roa": _number(values.get("roa")),
        "ebitda_margin": _ratio(ebitda, revenue, percent=True),
        "price_as_of": price_as_of,
        "fundamental_as_of": fundamental_as_of,
        "fundamental_publication_date": publication,
        "calculation_timestamp": _iso(calculated_at),
        "fundamental_vintage_id": vintage.get("fundamental_vintage_id"),
        "price_source": quote.get("provider_id") or quote.get("price_source") or "market_data_client",
        "fundamental_source": vintage.get("source") or "validated_warehouse",
        "calculation_version": CALCULATION_VERSION,
        "quality_status": "SUPPORTED" if not missing else "PARTIAL",
        "missing_inputs": missing,
        "source": "warehouse_reconstruction",
    }
    return {"ok": True, "status": row["quality_status"], "row": row}


def snapshot_decision(current: dict[str, Any], previous: dict[str, Any] | None, *, reason: str | None = None) -> dict[str, Any]:
    explicit = str(reason or "").upper()
    if explicit in EVENT_REASONS:
        return {"persist": True, "reason": explicit, "price_move_pct": None}
    if not previous:
        return {"persist": True, "reason": "INITIAL", "price_move_pct": None}
    old_price, new_price = _number(previous.get("price")), _number(current.get("price"))
    move = ((new_price / old_price - 1) * 100) if old_price and new_price else None
    if previous.get("fundamental_vintage_id") != current.get("fundamental_vintage_id"):
        return {"persist": True, "reason": "FINANCIAL_EVENT", "price_move_pct": move}
    try:
        old_ts = datetime.fromisoformat(str(previous.get("calculation_timestamp")).replace("Z", "+00:00"))
        new_ts = datetime.fromisoformat(str(current.get("calculation_timestamp")).replace("Z", "+00:00"))
        elapsed = (new_ts - old_ts).total_seconds() / 60
    except (TypeError, ValueError):
        elapsed = SNAPSHOT_INTERVAL_MINUTES
    if move is not None and abs(move) >= MATERIAL_PRICE_MOVE_PCT:
        return {"persist": True, "reason": "MATERIAL_PRICE_MOVE", "price_move_pct": round(move, 4)}
    if elapsed >= SNAPSHOT_INTERVAL_MINUTES:
        return {"persist": True, "reason": "INTERVAL_15M", "price_move_pct": round(move, 4) if move is not None else None}
    return {"persist": False, "reason": "LIVE_STATE_ONLY", "price_move_pct": round(move, 4) if move is not None else None}


def process_tick(*, quote: dict[str, Any], vintage: dict[str, Any], reason: str | None = None,
                 previous: dict[str, Any] | None = None, writer: Callable[..., dict[str, Any]] | None = None,
                 calculated_at: str | None = None) -> dict[str, Any]:
    result = calculate_state(quote=quote, vintage=vintage, calculated_at=calculated_at)
    if not result.get("ok"):
        return result
    row = result["row"]
    if previous is None:
        try:
            from institutional_warehouse import store
            prior = store.fetch("valuation_snapshots", entity=row["symbol"],
                                sort="calculation_timestamp", order="desc", limit=1).get("rows") or []
            previous = prior[0] if prior else None
        except Exception:
            previous = None
    decision = snapshot_decision(row, previous, reason=reason)
    if writer is None:
        from institutional_warehouse.gateway import write as writer
    live_write = writer("live_valuation_state", [row], source="warehouse_reconstruction",
                        actor="valuation_snapshot_engine", reason="refresh:live_valuation_state")
    snapshot_write = None
    if decision["persist"]:
        snapshot = {**row, "snapshot_reason": decision["reason"], "price_move_pct": decision["price_move_pct"]}
        snapshot_write = writer("valuation_snapshots", [snapshot], source="warehouse_reconstruction",
                                actor="valuation_snapshot_engine", reason=f"valuation_snapshot:{decision['reason'].lower()}")
    return {"ok": True, "status": result["status"], "decision": decision,
            "live_state": live_write, "snapshot": snapshot_write, "row": row}


async def refresh_symbol(symbol: str, *, client: Any = None, reason: str | None = None) -> dict[str, Any]:
    """Production worker entry point using existing governed market and financial layers."""
    if client is None:
        # This is AGI's existing Groww-first, fail-closed live quote chain. It
        # may itself use the configured live gateway; seeded equity prices are
        # explicitly rejected or replaced with an attributable fallback.
        from live_market_context.providers import fetch_best_quote
        live = fetch_best_quote(symbol, force=True)
        if not live.get("ok") or live.get("stale") or live.get("ltp") is None:
            return {"ok": False, "status": "LIVE_PRICE_UNAVAILABLE", "detail": live}
        quote = {
            "symbol": symbol.upper(), "last": live.get("ltp"), "volume": live.get("volume"),
            "price_as_of": live.get("as_of"), "provider_id": live.get("provider"),
        }
    else:
        quote_model = await client.get_quote(symbol)
        quote = quote_model.model_dump(mode="json")
        provenance = quote.get("provenance") or {}
        quote.update({"provider_id": provenance.get("provider_id"),
                      "price_as_of": provenance.get("vendor_as_of") or provenance.get("pulled_at")})
    from financial_engine.resolver import FinancialDataResolver
    facts = FinancialDataResolver().facts_for(symbol)
    vintage = build_fundamental_vintage(facts, price_as_of=_iso(quote.get("price_as_of")))
    return process_tick(quote=quote, vintage=vintage, reason=reason)


def latest_state(symbol: str) -> dict[str, Any]:
    from institutional_warehouse import store
    rows = store.fetch("live_valuation_state", entity=symbol.upper(), limit=1).get("rows") or []
    return {"ok": bool(rows), "status": "SUPPORTED" if rows else "DATA_REQUIRED",
            "symbol": symbol.upper(), "row": rows[0] if rows else None}


def snapshot_history(symbol: str, *, limit: int = 100) -> dict[str, Any]:
    from institutional_warehouse import store
    payload = store.fetch("valuation_snapshots", entity=symbol.upper(),
                          sort="calculation_timestamp", order="desc", limit=max(1, min(limit, 1000)))
    return {"ok": bool(payload.get("rows")), "symbol": symbol.upper(),
            "total": payload.get("total", 0), "rows": payload.get("rows") or []}


def health() -> dict[str, Any]:
    from institutional_warehouse.schema import tab_ids
    ids = set(tab_ids())
    return {
        "ok": {"live_valuation_state", "valuation_snapshots"} <= ids,
        "calculation_version": CALCULATION_VERSION,
        "live_state_table": "live_valuation_state",
        "permanent_snapshot_table": "valuation_snapshots",
        "fiscal_history_table": "sector_ratio_history",
        "snapshot_interval_minutes": SNAPSHOT_INTERVAL_MINUTES,
        "material_price_move_pct": MATERIAL_PRICE_MOVE_PCT,
        "pit_required": True, "overwrites_fiscal_history": False,
    }
