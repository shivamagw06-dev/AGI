#!/usr/bin/env python3
"""Ingest checked-in Trendlyne / Capital IQ exports into the warehouse.

Dry run (no credentials needed, prints what would be written):

    python3 scripts/ingest_vendor_exports.py

Write to the warehouse (needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):

    python3 scripts/ingest_vendor_exports.py --write

Dump parsed rows for inspection:

    python3 scripts/ingest_vendor_exports.py --dump historical_industry_medians --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "intelligence-engine"))

from financial_warehouse_completion import vendor_exports  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="persist to the warehouse")
    ap.add_argument("--dump", metavar="TAB", help="print parsed rows for one tab")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    result = vendor_exports.collect()

    print("=== source files parsed ===")
    for rep in result["reports"]:
        name = rep.get("path", "?")
        extra = ""
        if rep.get("skipped_no_symbol"):
            extra += f"  skipped_no_symbol={rep['skipped_no_symbol']}"
        if rep.get("consensus_covered") is not None:
            extra += f"  consensus_covered={rep['consensus_covered']}"
        print(f"  {name:44} rows_read={rep.get('rows_read'):>6}  as_of={rep.get('as_of')}{extra}")

    print("\n=== parsed rows by target ===")
    for tab, n in result["counts"].items():
        routed = "warehouse" if tab in vendor_exports.WAREHOUSE_TABS else "NO TAB YET"
        print(f"  {tab:32} {n:>6}   [{routed}]")

    if args.dump:
        rows = result["rows"].get(args.dump) or []
        print(f"\n=== {args.dump}: {len(rows)} rows (showing {min(args.limit, len(rows))}) ===")
        for row in rows[: args.limit]:
            print("  " + json.dumps(row, default=str))

    if not args.write:
        print("\nDry run. Re-run with --write to persist.")
        return 0

    import os
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY")):
        print("\nERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to --write.",
              file=sys.stderr)
        return 2

    outcome = vendor_exports.write(result["rows"])
    print("\n=== written ===")
    for tab, n in outcome["written"].items():
        print(f"  {tab:32} {n:>6}")
    if outcome["unrouted"]:
        print("\n=== parsed but NOT written (no warehouse tab defined) ===")
        for tab, n in outcome["unrouted"].items():
            print(f"  {tab:32} {n:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
