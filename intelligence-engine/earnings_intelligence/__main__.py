"""CLI: python -m earnings_intelligence TICKER [--quarters N] [--annuals N]."""

from __future__ import annotations

import json
import sys

from earnings_intelligence.production import analyse, health


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: python -m earnings_intelligence TICKER [--quarters N] [--annuals N] [--skip-xbrl]")
        print(json.dumps(health(), indent=2))
        return 0
    ticker = args[0].upper()
    q = 4
    a = 2
    skip = "--skip-xbrl" in args
    if "--quarters" in args:
        q = int(args[args.index("--quarters") + 1])
    if "--annuals" in args:
        a = int(args[args.index("--annuals") + 1])
    pack = analyse(ticker, quarterly_xbrl=q, annual_xbrl=a, skip_xbrl=skip, persist=False)
    slim = {
        "ticker": pack.get("ticker"),
        "ok": pack.get("ok"),
        "coverage_pct": pack.get("coverage_pct"),
        "cid_summary": pack.get("cid_summary"),
        "latest_quarter": {
            "period_end": (pack.get("latest_quarter") or {}).get("period_end"),
            "label": (pack.get("latest_quarter") or {}).get("quarter_label"),
            "revenue": ((pack.get("latest_quarter") or {}).get("income_statement") or {}).get("revenue_from_operations"),
            "pat": ((pack.get("latest_quarter") or {}).get("income_statement") or {}).get("pat"),
            "source": (pack.get("latest_quarter") or {}).get("source"),
        },
        "ttm_available": pack.get("ttm_available"),
        "segment_data": pack.get("segment_data"),
        "observations": (pack.get("intelligence") or {}).get("observations"),
        "errors": pack.get("errors"),
        "latency_ms": pack.get("latency_ms"),
    }
    print(json.dumps(slim, indent=2, default=str))
    return 0 if pack.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
