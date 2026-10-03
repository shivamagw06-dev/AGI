"""CLI: python -m portfolio_office --portfolio Core"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portfolio_office", description="PO-01 Portfolio Office")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--portfolio", metavar="NAME", help="Portfolio State Report for name/id")
    parser.add_argument("--summary", metavar="NAME", help="Summary / holdings totals")
    parser.add_argument("--snapshot", metavar="NAME", help="Take immutable snapshot")
    parser.add_argument("--create", metavar="NAME", help="Create empty/active portfolio by name")
    parser.add_argument("--list", action="store_true", dest="list_portfolios")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from portfolio_office.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from portfolio_office.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.list_portfolios:
        from portfolio_office import store as pf_store

        print(json.dumps(pf_store.list_portfolios(), indent=2, default=str))
        return 0
    if args.create:
        from portfolio_office.production import create

        print(json.dumps(create({"name": args.create}), indent=2, default=str))
        return 0
    if args.portfolio:
        from portfolio_office.production import get_portfolio

        print(json.dumps(get_portfolio(args.portfolio), indent=2, default=str))
        return 0
    if args.summary:
        from portfolio_office.production import get_holdings

        print(json.dumps(get_holdings(args.summary), indent=2, default=str))
        return 0
    if args.snapshot:
        from portfolio_office.production import snapshot

        print(json.dumps(snapshot(args.snapshot, {"kind": "manual"}), indent=2, default=str))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
