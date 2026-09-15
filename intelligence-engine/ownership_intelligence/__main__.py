"""CLI: python -m ownership_intelligence TICKER [--xbrl-quarters N]."""

from __future__ import annotations

import json
import sys

from ownership_intelligence.production import analyse, health


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: python -m ownership_intelligence TICKER [--xbrl-quarters N] [--skip-xbrl]")
        print(json.dumps(health(), indent=2))
        return 0
    ticker = args[0].upper()
    xq = 2
    skip = False
    if "--skip-xbrl" in args:
        skip = True
    if "--xbrl-quarters" in args:
        i = args.index("--xbrl-quarters")
        xq = int(args[i + 1])
    pack = analyse(ticker, xbrl_quarters=xq, skip_xbrl=skip, persist=False)
    # Compact print
    slim = {
        "ticker": pack.get("ticker"),
        "ok": pack.get("ok"),
        "as_of_quarter": pack.get("as_of_quarter"),
        "promoter": pack.get("promoter"),
        "fii": pack.get("fii"),
        "dii": pack.get("dii"),
        "mutual_funds": pack.get("mutual_funds"),
        "insurance": pack.get("insurance"),
        "public": pack.get("public"),
        "promoter_pledge": pack.get("promoter_pledge"),
        "promoter_pledge_pct": pack.get("promoter_pledge_pct"),
        "observations": (pack.get("intelligence") or {}).get("observations"),
        "ownership_quality": pack.get("ownership_quality"),
        "qoq": pack.get("qoq"),
        "history_count": len(pack.get("quarter_history") or []),
        "errors": pack.get("errors"),
    }
    print(json.dumps(slim, indent=2))
    return 0 if pack.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
