"""Load the full NSE cash equity trading universe (EQUITY_L → NIFTYstocks)."""

from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

TRADING_UNIVERSE_VERSION = "nse-equity-l-v1"
ALLOWED_SERIES = {"EQ", "BE", "SM"}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    # intelligence-engine/trading_universe → repo root
    return here.parents[2]


def universe_path() -> Path:
    """Prefer AGIB-normalized NIFTYstocks.csv; allow env override."""
    override = (os.getenv("NSE_TRADING_UNIVERSE_PATH") or os.getenv("NIFTY500_CONSTITUENTS_PATH") or "").strip()
    if override:
        p = Path(override)
        if p.exists():
            return p
    root = _repo_root()
    candidates = [
        root / "NIFTYstocks.csv",
        Path("/workspace/NIFTYstocks.csv"),
        Path.cwd() / "NIFTYstocks.csv",
        root / "Nifty500.csv",
        Path("/workspace/Nifty500.csv"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def equity_l_path() -> Path | None:
    root = _repo_root()
    for p in (root / "EQUITY_L.csv", Path("/workspace/EQUITY_L.csv"), Path.cwd() / "EQUITY_L.csv"):
        if p.exists():
            return p
    return None


def _row_symbol(row: dict[str, str]) -> str:
    for key in ("Symbol", "SYMBOL", "symbol", "Ticker", "ticker"):
        v = (row.get(key) or "").strip().upper()
        if v:
            return v
    return ""


@lru_cache(maxsize=4)
def _cached_rows(path_str: str, mtime_ns: int) -> tuple[dict[str, Any], ...]:
    path = Path(path_str)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        # Strip header whitespace (EQUITY_L raw has " SERIES")
        for raw in reader:
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
            symbol = _row_symbol(row)
            if not symbol:
                continue
            series = (row.get("Series") or row.get("SERIES") or "EQ").upper()
            if path.name.upper().startswith("EQUITY") and series not in ALLOWED_SERIES:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "name": row.get("Company Name")
                    or row.get("NAME OF COMPANY")
                    or row.get("Name")
                    or symbol,
                    "industry": row.get("Industry") or "NSE Equity",
                    "series": series,
                    "isin": row.get("ISIN Code") or row.get("ISIN NUMBER") or row.get("ISIN") or "",
                    "tradable": True,
                }
            )
    # Deterministic order
    rows.sort(key=lambda r: r["symbol"])
    return tuple(rows)


def load_rows(*, force: bool = False) -> list[dict[str, Any]]:
    path = universe_path()
    if not path.exists():
        return []
    if force:
        _cached_rows.cache_clear()
    st = path.stat()
    return list(_cached_rows(str(path), int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))))


def list_symbols(*, limit: int | None = None, series: str | None = None) -> list[str]:
    rows = load_rows()
    if series:
        want = series.upper().strip()
        rows = [r for r in rows if r.get("series") == want]
    symbols = [r["symbol"] for r in rows]
    if limit is not None:
        return symbols[: max(0, int(limit))]
    return symbols


def get_symbol(symbol: str) -> dict[str, Any] | None:
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    for row in load_rows():
        if row["symbol"] == sym:
            return dict(row)
    return None


def search(query: str, *, limit: int = 25) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: list[dict[str, Any]] = []
    for row in load_rows():
        if q in row["symbol"].lower() or q in str(row.get("name") or "").lower():
            hits.append(dict(row))
            if len(hits) >= max(1, min(int(limit), 200)):
                break
    return hits


def health() -> dict[str, Any]:
    path = universe_path()
    rows = load_rows() if path.exists() else []
    by_series: dict[str, int] = {}
    for r in rows:
        s = str(r.get("series") or "?")
        by_series[s] = by_series.get(s, 0) + 1
    return {
        "ok": bool(rows),
        "version": TRADING_UNIVERSE_VERSION,
        "path": str(path) if path.exists() else None,
        "equity_l_path": str(equity_l_path()) if equity_l_path() else None,
        "count": len(rows),
        "by_series": by_series,
        "role": "all_equity_stocks_available_for_trading",
        "source": "NSE EQUITY_L (EQ/BE/SM)",
    }


def dashboard(*, include_sample: bool = True) -> dict[str, Any]:
    h = health()
    sample = list_symbols(limit=20) if include_sample else []
    return {
        **h,
        "sample_symbols": sample,
        "contains_idbi": "IDBI" in set(list_symbols()),
        "actions": ["list", "search", "get_symbol", "refresh_via_refresh_nifty_stocks_py"],
    }
