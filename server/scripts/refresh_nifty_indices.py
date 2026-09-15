#!/usr/bin/env python3
"""Refresh repo `indices/*.csv` from NSE Indices or local Market Watch CSVs.

Usage:
  # Pull official constituent lists
  python3 server/scripts/refresh_nifty_indices.py

  # Ingest NSE Market Watch downloads (MW-NIFTY-*.csv)
  python3 server/scripts/refresh_nifty_indices.py --mw-dir ~/Downloads
  python3 server/scripts/refresh_nifty_indices.py --in MW-NIFTY-BANK-30-Jul-2026.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "indices"

# Official NSE Indices constituent files (Company Name,Industry,Symbol,Series,ISIN Code)
OFFICIAL: dict[str, tuple[str, str]] = {
    # index_id → (outfile, url path under IndexConstituent/)
    "NIFTY_50": ("Nifty50.csv", "ind_nifty50list.csv"),
    "NIFTY_NEXT_50": ("NiftyNext50.csv", "ind_niftynext50list.csv"),
    "NIFTY_100": ("Nifty100.csv", "ind_nifty100list.csv"),
    "NIFTY_200": ("Nifty200.csv", "ind_nifty200list.csv"),
    "NIFTY_500": ("Nifty500.csv", "ind_nifty500list.csv"),
    "NIFTY_MIDCAP_SELECT": ("NiftyMidcapSelect.csv", "ind_niftymidcapselect_list.csv"),
    "NIFTY_BANK": ("NiftyBank.csv", "ind_niftybanklist.csv"),
    "NIFTY_FINANCIAL_SERVICES": ("NiftyFinancialServices.csv", "ind_niftyfinancelist.csv"),
}

BASE_URL = "https://www.niftyindices.com/IndexConstituent/"

# Filename patterns for NSE Market Watch exports → index_id
MW_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"MW-NIFTY-500", re.I), "NIFTY_500"),
    (re.compile(r"MW-NIFTY-200", re.I), "NIFTY_200"),
    (re.compile(r"MW-NIFTY-100", re.I), "NIFTY_100"),
    (re.compile(r"MW-NIFTY-NEXT-50", re.I), "NIFTY_NEXT_50"),
    (re.compile(r"MW-NIFTY-MIDCAP-SELECT", re.I), "NIFTY_MIDCAP_SELECT"),
    (re.compile(r"MW-NIFTY-FINANCIAL-SERVICES", re.I), "NIFTY_FINANCIAL_SERVICES"),
    (re.compile(r"MW-NIFTY-BANK", re.I), "NIFTY_BANK"),
    (re.compile(r"MW-NIFTY-50(?!-)", re.I), "NIFTY_50"),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB/1.0)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8-sig")


def write_normalized(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Company Name", "Industry", "Symbol", "Series", "ISIN Code"],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_official(raw: str) -> list[dict[str, str]]:
    reader = csv.DictReader(raw.splitlines())
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_row in reader:
        row = {(k or "").strip(): (v or "").strip() for k, v in raw_row.items()}
        symbol = (row.get("Symbol") or row.get("SYMBOL") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(
            {
                "Company Name": row.get("Company Name") or symbol,
                "Industry": row.get("Industry") or "",
                "Symbol": symbol,
                "Series": (row.get("Series") or "EQ").upper(),
                "ISIN Code": row.get("ISIN Code") or "",
            }
        )
    return out


def parse_market_watch(raw: str) -> list[dict[str, str]]:
    """NSE Market Watch CSV — SYMBOL column; first row often the index itself."""
    reader = csv.DictReader(raw.splitlines())
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_row in reader:
        row = {(k or "").strip().strip('"'): (v or "").strip().strip('"') for k, v in raw_row.items()}
        symbol = (row.get("SYMBOL") or row.get("Symbol") or "").upper()
        if not symbol or symbol in seen:
            continue
        # Drop the index summary row
        if "NIFTY" in symbol or symbol in {"BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}:
            continue
        if not re.fullmatch(r"[A-Z0-9&-]{1,15}", symbol):
            continue
        seen.add(symbol)
        out.append(
            {
                "Company Name": row.get("SYMBOL") or symbol,
                "Industry": "",
                "Symbol": symbol,
                "Series": "EQ",
                "ISIN Code": "",
            }
        )
    return out


def detect_mw_index(path: Path) -> str | None:
    name = path.name
    for pattern, iid in MW_PATTERNS:
        if pattern.search(name):
            return iid
    return None


def refresh_official(out_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for iid, (filename, remote) in OFFICIAL.items():
        url = BASE_URL + remote
        raw = fetch(url)
        if "<html" in raw[:200].lower():
            raise SystemExit(f"Failed to fetch {url} (got HTML)")
        rows = parse_official(raw)
        if not rows:
            raise SystemExit(f"No rows from {url}")
        write_normalized(out_dir / filename, rows)
        counts[iid] = len(rows)
        # Keep root Nifty500.csv in sync for legacy loaders
        if iid == "NIFTY_500":
            write_normalized(REPO_ROOT / "Nifty500.csv", rows)
    return counts


def ingest_mw_files(paths: list[Path], out_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in paths:
        iid = detect_mw_index(path)
        if not iid:
            print(f"skip (unknown MW pattern): {path.name}")
            continue
        filename = OFFICIAL[iid][0]
        rows = parse_market_watch(path.read_text(encoding="utf-8-sig"))
        if not rows:
            print(f"skip (empty): {path.name}")
            continue
        write_normalized(out_dir / filename, rows)
        counts[iid] = len(rows)
        print(f"{path.name} → {filename} ({len(rows)} symbols)")
        if iid == "NIFTY_500":
            write_normalized(REPO_ROOT / "Nifty500.csv", rows)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Nifty index constituent CSVs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--mw-dir", type=Path, help="Directory of MW-NIFTY-*.csv downloads")
    parser.add_argument("--in", dest="infile", type=Path, action="append", default=[], help="One MW CSV")
    parser.add_argument("--official-only", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    mw_paths: list[Path] = list(args.infile)
    if args.mw_dir:
        mw_paths.extend(sorted(args.mw_dir.glob("MW-NIFTY*.csv")))

    if mw_paths and not args.official_only:
        counts = ingest_mw_files(mw_paths, args.out)
    else:
        counts = refresh_official(args.out)

    print("Index constituent counts:")
    for iid, n in sorted(counts.items()):
        print(f"  {iid}: {n}")
    print(f"Wrote under {args.out}")


if __name__ == "__main__":
    main()
