"""Normalise Upstox key-ratios into warehouse.valuation_ratios + historical_valuation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

SOURCE = "upstox"
PROVIDER_VERSION = "v2/fundamentals/key-ratios"

# Upstox name → warehouse ratio_name
_RATIO_MAP = {
    "p/e": "pe",
    "pe": "pe",
    "p/b": "pb",
    "pb": "pb",
    "roa": "roa",
    "roe": "roe",
    "roce": "roce",
    "ev/ebitda": "ev_ebitda",
    "ev_ebitda": "ev_ebitda",
    "evebitda": "ev_ebitda",
}

# Ratios the Unified Valuation Engine must prefer from the provider.
PROVIDER_OWNED = frozenset({"pe", "pb", "roa", "roe", "roce", "ev_ebitda"})


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text.lower() in {"na", "n/a", "-", "null", "none"}:
        return None
    try:
        out = float(text)
    except (TypeError, ValueError):
        return None
    return None if out != out else out


def _validate_ratio(name: str, company: Optional[float], sector: Optional[float]) -> tuple[str, str]:
    """Return (dqiv_status, notes). Never rejects the raw row — records status only."""
    notes: list[str] = []
    if company is None:
        return "missing", "company_value missing"
    if name in {"pe", "pb", "ev_ebitda"} and company <= 0:
        notes.append("non_positive_multiple")
    if name in {"roa", "roe", "roce"} and abs(company) > 200:
        notes.append("impossible_percentage")
    if name == "pe" and company > 500:
        notes.append("extreme_pe")
    if name == "pb" and company > 100:
        notes.append("extreme_pb")
    if sector is None:
        notes.append("sector_benchmark_missing")
    if notes:
        return "warning", ";".join(notes)
    return "passed", ""


def normalise_upstox_key_ratios(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One Upstox key-ratios response → append-only warehouse rows."""
    symbol = str(payload.get("symbol") or "").strip().upper()
    isin = str(payload.get("isin") or "").strip().upper()
    if not symbol or not isin:
        return []

    company_id = str(payload.get("company_id") or symbol)
    instrument_key = str(payload.get("instrument_key") or f"NSE_EQ|{isin}")
    now = datetime.now(timezone.utc)
    reported_date = str(payload.get("reported_date") or now.date().isoformat())
    reported_time = str(payload.get("reported_time") or now.isoformat())
    # Deterministic per company and day, because snapshot_id is part of the key.
    # A random one made a re-run land a second row for the same company on the
    # same date - which is a duplicate, not a second observation. A sweep that
    # retries a failed company must produce one final snapshot, not two.
    snapshot_id = str(payload.get("snapshot_id")
                      or f"upstox-{reported_date}-{symbol}")

    raw = payload.get("data")
    if raw is None:
        raw = payload.get("ratios") or payload.get("key_ratios") or []
    if isinstance(raw, dict):
        # Already keyed {pe: {company, sector}, ...}
        entries = []
        for key, block in raw.items():
            if isinstance(block, dict):
                entries.append({
                    "name": key,
                    "company_value": block.get("company_value", block.get("value")),
                    "sector_value": block.get("sector_value", block.get("sector")),
                })
            else:
                entries.append({"name": key, "company_value": block, "sector_value": None})
        raw = entries

    rows: list[dict[str, Any]] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        mapped = _RATIO_MAP.get(str(item.get("name") or "").strip().lower())
        if not mapped:
            continue
        company_value = _num(item.get("company_value"))
        sector_value = _num(item.get("sector_value"))
        status, notes = _validate_ratio(mapped, company_value, sector_value)
        if company_value is None:
            continue
        rows.append({
            "company_id": company_id,
            "symbol": symbol,
            "isin": isin,
            "instrument_key": instrument_key,
            "ratio_name": mapped,
            "company_value": round(company_value, 6),
            "sector_value": round(sector_value, 6) if sector_value is not None else None,
            "reported_date": reported_date,
            "reported_time": reported_time,
            "snapshot_id": snapshot_id,
            "provider": SOURCE,
            "provider_version": PROVIDER_VERSION,
            # Numeric band (0–1). Text "high" crashed older warehouse validators
            # that applied IMPOSSIBLE["confidence"] via float().
            "confidence": 0.9 if status == "passed" else 0.7,
            "dqiv_status": status,
            "validation_notes": notes,
            "source": SOURCE,
        })
    return rows


def ingest_key_ratios(
    rows: list[dict[str, Any]],
    *,
    actor: str = "valuation_ratios",
    sync_valuation: bool = True,
) -> dict[str, Any]:
    """Write long-format ratios via DQIV; optionally pivot into historical_valuation."""
    from institutional_warehouse import gateway

    if not rows:
        return {"ok": False, "error": "no_rows"}

    result = gateway.write("valuation_ratios", rows, source=SOURCE, actor=actor)
    out: dict[str, Any] = {"ok": True, "valuation_ratios": result, "rows": len(rows)}

    if sync_valuation:
        out["historical_valuation"] = sync_historical_valuation(rows, actor=actor)
    return out



def _closing_prices(symbols: set[str], dates: set[str]) -> dict[tuple[str, str], float]:
    """Closing price per (symbol, date), in one query rather than 2,400.

    Only the dates being written are looked up. Carrying a stale close forward
    onto today's row would print a price the market never traded at, which is
    worse than showing none.
    """
    from institutional_warehouse import db

    if not symbols or not dates:
        return {}
    table = db.physical_table("daily_market_history")
    marks = ",".join(["?"] * len(dates))
    rows = db.query(
        f"SELECT symbol, date, close FROM {table} "
        f"WHERE date IN ({marks}) AND close IS NOT NULL",
        tuple(sorted(dates)),
    )
    out: dict[tuple[str, str], float] = {}
    for row in rows:
        sym = str(row.get("symbol") or "").upper()
        if sym not in symbols:
            continue
        try:
            out[(sym, str(row.get("date")))] = float(row["close"])
        except (TypeError, ValueError):
            continue
    return out


def _existing_valuations(symbols: set[str], dates: set[str]) -> dict[tuple[str, str], dict[str, Any]]:
    """What the table already holds for these keys, in one query.

    The per-symbol fetch this replaces ran once per company: a full sweep of
    2,400 companies meant 2,400 round trips before a single row was written.
    """
    from institutional_warehouse import db

    if not symbols or not dates:
        return {}
    table = db.physical_table("historical_valuation")
    marks = ",".join(["?"] * len(dates))
    rows = db.query(f"SELECT * FROM {table} WHERE date IN ({marks})",
                    tuple(sorted(dates)))
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        sym = str(row.get("symbol") or "").upper()
        if sym in symbols:
            out[(sym, str(row.get("date")))] = row
    return out

def sync_historical_valuation(
    ratio_rows: list[dict[str, Any]],
    *,
    actor: str = "valuation_ratios",
) -> dict[str, Any]:
    """Pivot provider PE/PB/EV into historical_valuation (vendor-owned multiples)."""
    from institutional_warehouse import gateway, store

    by_symbol: dict[str, dict[str, Any]] = {}
    for row in ratio_rows:
        sym = str(row.get("symbol") or "").upper()
        name = str(row.get("ratio_name") or "")
        if not sym or name not in {"pe", "pb", "ev_ebitda", "roe", "roa", "roce"}:
            continue
        bucket = by_symbol.setdefault(sym, {
            "date": row.get("reported_date"),
            "symbol": sym,
            "source": SOURCE,
        })
        bucket[name] = row.get("company_value")
        if name == "pe" and row.get("sector_value") is not None:
            bucket["sector_median"] = row.get("sector_value")
        if name == "pb" and row.get("sector_value") is not None:
            bucket["industry_median"] = row.get("sector_value")  # store sector PB as industry_median proxy until dedicated cols

    if not by_symbol:
        return {"ok": True, "wrote": 0, "note": "no_pivot_rows"}

    # Preserve CMP / market_cap already on today's valuation row, and fill CMP
    # from the price history when nothing holds one.
    #
    # Yahoo used to write both the multiples and the price into this table.
    # It was stopped as a source of valuation ratios, and the Upstox key-ratios
    # endpoint carries no price at all, so CMP had no writer left: coverage of
    # this table fell from 2,889 rows on 19 August to 82 on the 23rd, and the
    # sector desk reads it for the price it shows. daily_market_history is
    # collected every thirty minutes and is current, so the price is taken
    # from there rather than reintroducing the provider.
    dates = {row.get("date") for row in by_symbol.values() if row.get("date")}
    closes = _closing_prices(set(by_symbol), dates)

    staged: list[dict[str, Any]] = []
    held_rows = _existing_valuations(set(by_symbol), dates)
    for sym, row in by_symbol.items():
        held = held_rows.get((sym, str(row.get("date") or ""))) or {}
        merged = {**held, **row, "source": SOURCE}
        if merged.get("cmp") is None:
            close = closes.get((sym, str(row.get("date") or "")))
            if close is not None:
                merged["cmp"] = close
        # Drop identity columns that are not in historical_valuation schema.
        for drop in ("company_id", "isin", "instrument_key", "ratio_name", "company_value",
                     "sector_value", "reported_date", "reported_time", "snapshot_id",
                     "provider", "provider_version", "confidence", "dqiv_status",
                     "validation_notes", "roa", "roe", "roce"):
            merged.pop(drop, None)
        staged.append(merged)

    result = gateway.write("historical_valuation", staged, source=SOURCE, actor=actor)
    return {"ok": True, **result}


def latest_provider_ratios(symbol: str) -> dict[str, Any]:
    """Latest Upstox ratio pack for one company (for engine overlay)."""
    from institutional_warehouse import store

    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "symbol": ticker, "ratios": {}}

    rows = store.fetch("valuation_ratios", filters={"symbol": ticker}, limit=40).get("rows") or []
    # Prefer newest reported_date.
    rows = sorted(rows, key=lambda r: str(r.get("reported_date") or ""), reverse=True)
    ratios: dict[str, dict[str, Any]] = {}
    as_of = None
    for row in rows:
        name = str(row.get("ratio_name") or "")
        if name not in PROVIDER_OWNED or name in ratios:
            continue
        ratios[name] = {
            "company_value": row.get("company_value"),
            "sector_value": row.get("sector_value"),
            "reported_date": row.get("reported_date"),
            "dqiv_status": row.get("dqiv_status"),
            "confidence": row.get("confidence"),
            "source": row.get("source") or SOURCE,
            "snapshot_id": row.get("snapshot_id"),
        }
        as_of = as_of or row.get("reported_date")

    return {
        "ok": bool(ratios),
        "symbol": ticker,
        "as_of": as_of,
        "source": SOURCE,
        "ratios": ratios,
    }
