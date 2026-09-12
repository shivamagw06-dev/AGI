"""Backfill company_master.isin from Upstox NSE equity instruments.

Upstox fundamentals require ISIN (`GET /fundamentals/{isin}/key-ratios`).
Production company_master historically had symbols but null ISINs, which
blocked the entire valuation_ratios pipeline.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Optional

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
UPSTOX_NSE_INSTRUMENTS = (
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
)


def _valid_isin(value: Any) -> Optional[str]:
    text = str(value or "").strip().upper()
    return text if ISIN_RE.match(text) else None


def load_upstox_nse_isin_map(
    *,
    url: str = UPSTOX_NSE_INSTRUMENTS,
    timeout_s: int = 90,
) -> dict[str, dict[str, str]]:
    """Map NSE trading_symbol → {isin, instrument_key, name} for EQ listings."""
    req = urllib.request.Request(url, headers={"User-Agent": "AGIB-ISIN-Backfill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
    if url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    out: dict[str, dict[str, str]] = {}
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("segment") != "NSE_EQ":
            continue
        if str(item.get("instrument_type") or "").upper() != "EQ":
            continue
        symbol = str(item.get("trading_symbol") or "").strip().upper()
        isin = _valid_isin(item.get("isin"))
        if not symbol or not isin:
            continue
        out[symbol] = {
            "isin": isin,
            "instrument_key": str(item.get("instrument_key") or f"NSE_EQ|{isin}"),
            "name": str(item.get("name") or symbol),
        }
    return out


def load_index_csv_isin_map(indices_dir: Optional[Path] = None) -> dict[str, str]:
    """Optional secondary map from repo indices/*.csv (Symbol, ISIN Code)."""
    root = indices_dir or Path(__file__).resolve().parents[2] / "indices"
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.csv")):
        try:
            with path.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    symbol = str(row.get("Symbol") or row.get("symbol") or "").strip().upper()
                    isin = _valid_isin(row.get("ISIN Code") or row.get("ISIN") or row.get("isin"))
                    if symbol and isin:
                        out.setdefault(symbol, isin)
        except OSError:
            continue
    return out


def backfill_company_isins(
    *,
    actor: str = "isin_backfill",
    dry_run: bool = False,
    prefer_csv: bool = True,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """Fill missing company_master.isin via warehouse gateway write."""
    from institutional_warehouse import gateway, store

    upstox_map = load_upstox_nse_isin_map()
    csv_map = load_index_csv_isin_map() if prefer_csv else {}

    masters = store.all_rows("company_master", limit=limit or 10_000)
    updates: list[dict[str, Any]] = []
    already = matched = missing = 0

    for master in masters:
        symbol = str(master.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        existing = _valid_isin(master.get("isin"))
        if existing:
            already += 1
            continue
        hit = upstox_map.get(symbol)
        isin = (hit or {}).get("isin") if hit else None
        if not isin:
            isin = csv_map.get(symbol)
        if not isin:
            missing += 1
            continue
        matched += 1
        updates.append({
            "company_id": master.get("company_id") or symbol,
            "symbol": symbol,
            "company_name": master.get("company_name") or symbol,
            "isin": isin,
            "exchange": master.get("exchange") or "NSE",
        })

    if dry_run or not updates:
        return {
            "ok": True,
            "dry_run": dry_run,
            "masters": len(masters),
            "already_had_isin": already,
            "matched": matched,
            "unmatched": missing,
            "upstox_eq_map": len(upstox_map),
            "csv_map": len(csv_map),
            "would_write": len(updates),
            "written": 0,
            "sample": updates[:10],
        }

    # Chunk writes to keep validation payloads bounded.
    written = inserted = updated = unchanged = quarantined = 0
    for start in range(0, len(updates), 250):
        chunk = updates[start:start + 250]
        result = gateway.write(
            "company_master",
            chunk,
            source="upstox_instruments",
            actor=actor,
            reason="isin_backfill",
            detect_conflicts=False,
        )
        written += int(result.get("written") or 0)
        inserted += int(result.get("inserted") or 0)
        updated += int(result.get("updated") or 0)
        unchanged += int(result.get("unchanged") or 0)
        quarantined += int(result.get("quarantined") or 0)

    return {
        "ok": quarantined == 0,
        "dry_run": False,
        "masters": len(masters),
        "already_had_isin": already,
        "matched": matched,
        "unmatched": missing,
        "upstox_eq_map": len(upstox_map),
        "csv_map": len(csv_map),
        "written": written,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "quarantined": quarantined,
        "sample": updates[:10],
    }
