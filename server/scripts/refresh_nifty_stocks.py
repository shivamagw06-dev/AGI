#!/usr/bin/env python3
"""Refresh NIFTYstocks.csv from the official NSE equity securities list.

Usage:
  python3 server/scripts/refresh_nifty_stocks.py
  python3 server/scripts/refresh_nifty_stocks.py --in EQUITY_L.csv
  python3 server/scripts/refresh_nifty_stocks.py --out /path/to/NIFTYstocks.csv

Merges Industry labels from Nifty500.csv when available.
Does not place orders or invent fundamentals.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import urllib.request
from pathlib import Path

NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "NIFTYstocks.csv"
DEFAULT_EQUITY_L = REPO_ROOT / "EQUITY_L.csv"
NIFTY500_PATH = REPO_ROOT / "Nifty500.csv"
ALLOWED_SERIES = {"EQ", "BE", "SM"}


def fetch_equity_csv(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-research/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def load_nifty500_industries(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    industries: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = (row.get("Symbol") or row.get("symbol") or "").strip().upper()
            industry = (row.get("Industry") or "").strip()
            if symbol and industry:
                industries[symbol] = industry
    return industries


def normalize_rows(raw_csv: str, industries: dict[str, str]) -> list[dict[str, str]]:
    reader = csv.DictReader(raw_csv.splitlines())
    field_map = {(k or "").strip().upper(): k for k in (reader.fieldnames or [])}

    def cell(row: dict[str, str], name: str) -> str:
        key = field_map.get(name.upper())
        if key is None:
            return ""
        return (row.get(key) or "").strip()

    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for row in reader:
        symbol = cell(row, "SYMBOL").upper()
        series = cell(row, "SERIES").upper()
        if not symbol or series not in ALLOWED_SERIES or symbol in seen:
            continue
        seen.add(symbol)
        rows.append(
            {
                "Company Name": cell(row, "NAME OF COMPANY"),
                "Industry": industries.get(symbol, "NSE Equity"),
                "Symbol": symbol,
                "Series": series,
                "ISIN Code": cell(row, "ISIN NUMBER"),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Company Name", "Industry", "Symbol", "Series", "ISIN Code"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh NIFTYstocks.csv from NSE EQUITY_L")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--in",
        dest="infile",
        type=Path,
        default=None,
        help="Local EQUITY_L.csv (skip network fetch)",
    )
    parser.add_argument("--url", default=NSE_EQUITY_URL)
    parser.add_argument(
        "--keep-equity-l",
        type=Path,
        default=DEFAULT_EQUITY_L,
        help="Also write/copy raw EQUITY_L.csv to this path (default: repo root)",
    )
    parser.add_argument("--no-keep-equity-l", action="store_true")
    args = parser.parse_args()

    industries = load_nifty500_industries(NIFTY500_PATH)
    if args.infile:
        if not args.infile.exists():
            raise SystemExit(f"Input not found: {args.infile}")
        raw = args.infile.read_text(encoding="utf-8-sig")
        source = str(args.infile)
        if not args.no_keep_equity_l and args.keep_equity_l:
            args.keep_equity_l.parent.mkdir(parents=True, exist_ok=True)
            if args.infile.resolve() != args.keep_equity_l.resolve():
                shutil.copyfile(args.infile, args.keep_equity_l)
            print(f"Stored raw EQUITY_L → {args.keep_equity_l}")
    else:
        raw = fetch_equity_csv(args.url)
        source = args.url
        if not args.no_keep_equity_l and args.keep_equity_l:
            args.keep_equity_l.parent.mkdir(parents=True, exist_ok=True)
            args.keep_equity_l.write_text(raw, encoding="utf-8")
            print(f"Stored raw EQUITY_L → {args.keep_equity_l}")

    rows = normalize_rows(raw, industries)
    if not rows:
        raise SystemExit("No EQ/BE/SM symbols parsed from NSE equity list")
    write_csv(args.out, rows)
    labeled = sum(1 for row in rows if row["Industry"] != "NSE Equity")
    print(f"Source: {source}")
    print(f"Wrote {len(rows)} NSE equities (EQ/BE/SM) → {args.out}")
    print(f"Industry labels from Nifty500: {labeled}")


if __name__ == "__main__":
    main()
