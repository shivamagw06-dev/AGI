"""Load Nifty / NSE index constituent CSVs from repo `indices/`."""

from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

MARKET_INDICES_VERSION = "nifty-indices-v1"

# Canonical catalog — files live under repo-root/indices/
INDEX_CATALOG: dict[str, dict[str, Any]] = {
    "NIFTY_50": {
        "index_id": "NIFTY_50",
        "display_name": "Nifty 50",
        "aliases": ("nifty 50", "nifty50", "nse:nifty50"),
        "file": "Nifty50.csv",
        "family": "india_nifty",
        "parent": "NIFTY_100",
        "tier": 1,
        "quote_symbol": "NIFTY",
    },
    "NIFTY_NEXT_50": {
        "index_id": "NIFTY_NEXT_50",
        "display_name": "Nifty Next 50",
        "aliases": ("nifty next 50", "nifty next50", "niftynxt50", "next 50"),
        "file": "NiftyNext50.csv",
        "family": "india_nifty",
        "parent": "NIFTY_100",
        "tier": 1,
        "quote_symbol": "NIFTYNXT50",
    },
    "NIFTY_100": {
        "index_id": "NIFTY_100",
        "display_name": "Nifty 100",
        "aliases": ("nifty 100", "nifty100"),
        "file": "Nifty100.csv",
        "family": "india_nifty",
        "parent": "NIFTY_200",
        "tier": 1,
        "quote_symbol": "NIFTY100",
    },
    "NIFTY_200": {
        "index_id": "NIFTY_200",
        "display_name": "Nifty 200",
        "aliases": ("nifty 200", "nifty200"),
        "file": "Nifty200.csv",
        "family": "india_nifty",
        "parent": "NIFTY_500",
        "tier": 2,
        "quote_symbol": "NIFTY200",
    },
    "NIFTY_500": {
        "index_id": "NIFTY_500",
        "display_name": "Nifty 500",
        "aliases": ("nifty 500", "nifty500"),
        "file": "Nifty500.csv",
        "family": "india_nifty",
        "parent": None,
        "tier": 2,
        "quote_symbol": "NIFTY500",
    },
    "NIFTY_MIDCAP_SELECT": {
        "index_id": "NIFTY_MIDCAP_SELECT",
        "display_name": "Nifty Midcap Select",
        "aliases": ("nifty midcap select", "midcap select", "nifty midcapselect"),
        "file": "NiftyMidcapSelect.csv",
        "family": "india_nifty",
        "parent": "NIFTY_500",
        "tier": 2,
        "quote_symbol": "MIDCPNIFTY",
    },
    "NIFTY_BANK": {
        "index_id": "NIFTY_BANK",
        "display_name": "Nifty Bank",
        "aliases": ("nifty bank", "bank nifty", "banknifty", "niftybank"),
        "file": "NiftyBank.csv",
        "family": "india_thematic",
        "parent": None,
        "tier": 2,
        "quote_symbol": "BANKNIFTY",
    },
    "NIFTY_FINANCIAL_SERVICES": {
        "index_id": "NIFTY_FINANCIAL_SERVICES",
        "display_name": "Nifty Financial Services",
        "aliases": (
            "nifty financial services",
            "nifty finance",
            "fin nifty",
            "finnifty",
            "financial services index",
        ),
        "file": "NiftyFinancialServices.csv",
        "family": "india_thematic",
        "parent": None,
        "tier": 2,
        "quote_symbol": "FINNIFTY",
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def indices_dir() -> Path:
    override = (os.getenv("NSE_INDICES_DIR") or "").strip()
    if override:
        p = Path(override)
        if p.exists():
            return p
    root = _repo_root()
    for p in (root / "indices", Path("/workspace/indices"), Path.cwd() / "indices"):
        if p.exists():
            return p
    return root / "indices"


def _normalize_index_id(value: str) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    up = raw.upper().replace(" ", "_").replace("-", "_")
    if up in INDEX_CATALOG:
        return up
    low = raw.lower().strip()
    # Prefer longer aliases first so "nifty next 50" wins over "nifty 50"
    alias_hits: list[tuple[int, str]] = []
    for iid, meta in INDEX_CATALOG.items():
        names = list(meta["aliases"]) + [str(meta["display_name"]).lower()]
        for alias in names:
            a = alias.lower().strip()
            if not a:
                continue
            if low == a or a in low:
                alias_hits.append((len(a), iid))
        if up == meta.get("quote_symbol"):
            return iid
    if alias_hits:
        alias_hits.sort(key=lambda x: -x[0])
        return alias_hits[0][1]
    return None


def _read_constituent_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
            symbol = (
                row.get("Symbol")
                or row.get("SYMBOL")
                or row.get("symbol")
                or row.get("Ticker")
                or ""
            ).upper()
            if not symbol:
                continue
            # Skip index header rows from Market Watch exports
            if symbol.startswith("NIFTY") or symbol in {"BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "name": row.get("Company Name") or row.get("NAME OF COMPANY") or symbol,
                    "industry": row.get("Industry") or "",
                    "series": (row.get("Series") or row.get("SERIES") or "EQ").upper(),
                    "isin": row.get("ISIN Code") or row.get("ISIN NUMBER") or row.get("ISIN") or "",
                }
            )
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        if r["symbol"] in seen:
            continue
        seen.add(r["symbol"])
        out.append(r)
    return out


@lru_cache(maxsize=32)
def _cached_members(index_id: str, path_str: str, mtime_ns: int) -> tuple[dict[str, Any], ...]:
    return tuple(_read_constituent_csv(Path(path_str)))


def list_indices() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for iid, meta in INDEX_CATALOG.items():
        path = indices_dir() / meta["file"]
        members = list_members(iid) if path.exists() else []
        out.append(
            {
                "index_id": iid,
                "display_name": meta["display_name"],
                "family": meta["family"],
                "parent": meta.get("parent"),
                "tier": meta.get("tier"),
                "quote_symbol": meta.get("quote_symbol"),
                "file": meta["file"],
                "path": str(path) if path.exists() else None,
                "count": len(members),
                "available": path.exists(),
            }
        )
    return out


def list_members(index_id: str) -> list[dict[str, Any]]:
    iid = _normalize_index_id(index_id) or (index_id or "").upper()
    meta = INDEX_CATALOG.get(iid)
    if not meta:
        return []
    path = indices_dir() / meta["file"]
    if not path.exists():
        return []
    st = path.stat()
    return list(_cached_members(iid, str(path), int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))))


def get_index(index_id: str, *, include_members: bool = True) -> dict[str, Any] | None:
    iid = _normalize_index_id(index_id)
    if not iid:
        return None
    meta = INDEX_CATALOG[iid]
    members = list_members(iid)
    body: dict[str, Any] = {
        "ok": True,
        "index_id": iid,
        "display_name": meta["display_name"],
        "aliases": list(meta["aliases"]),
        "family": meta["family"],
        "parent": meta.get("parent"),
        "tier": meta.get("tier"),
        "quote_symbol": meta.get("quote_symbol"),
        "file": meta["file"],
        "count": len(members),
        "version": MARKET_INDICES_VERSION,
    }
    if include_members:
        body["members"] = members
        body["symbols"] = [m["symbol"] for m in members]
    return body


def membership_for_symbol(symbol: str) -> dict[str, Any]:
    sym = (symbol or "").strip().upper()
    hits: list[str] = []
    for iid in INDEX_CATALOG:
        if any(m["symbol"] == sym for m in list_members(iid)):
            hits.append(iid)
    return {
        "ok": True,
        "symbol": sym,
        "indices": hits,
        "count": len(hits),
    }


def search_index(query: str) -> dict[str, Any] | None:
    return get_index(query, include_members=True)


def health() -> dict[str, Any]:
    indices = list_indices()
    return {
        "ok": any(i["available"] for i in indices),
        "version": MARKET_INDICES_VERSION,
        "indices_dir": str(indices_dir()),
        "index_count": len(indices),
        "available_count": sum(1 for i in indices if i["available"]),
        "total_memberships": sum(int(i["count"]) for i in indices),
        "indices": indices,
        "role": "index_constituent_registry",
        "source": "NSE Indices / Market Watch constituent CSVs",
    }


def dashboard() -> dict[str, Any]:
    h = health()
    samples = {
        i["index_id"]: list_members(i["index_id"])[:5]
        for i in h["indices"]
        if i["available"]
    }
    return {**h, "sample_members": samples}
