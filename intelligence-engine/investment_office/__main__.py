"""CLI: python -m investment_office --company TCS | --question "..." [--ticker TCS]"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="investment_office",
        description="IO-01 Investment Office — orchestrate FIRE into Institutional Research Packages",
    )
    parser.add_argument("--company", metavar="TICKER", help="Assemble institutional brief for ticker")
    parser.add_argument("--question", metavar="TEXT", help="Route and answer an investment question")
    parser.add_argument("--ticker", metavar="TICKER", help="Ticker for --question (default TCS)")
    parser.add_argument("--package", metavar="TYPE", help="Explicit package type override")
    parser.add_argument("--health", action="store_true", help="Health probe")
    parser.add_argument("--dashboard", action="store_true", help="Desk dashboard")
    parser.add_argument("--metrics", action="store_true", help="IO-01 orchestration metrics")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from investment_office.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from investment_office.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.metrics:
        from investment_office import store as io_store

        print(json.dumps(io_store.irp_metrics(), indent=2, default=str))
        return 0

    if args.company:
        from investment_office.production import company

        print(
            json.dumps(
                company(args.company, package_type=args.package),
                indent=2,
                default=str,
            )
        )
        return 0

    if args.question:
        from investment_office.production import query

        ticker = args.ticker or "TCS"
        print(
            json.dumps(
                query(ticker=ticker, question=args.question, package_type=args.package),
                indent=2,
                default=str,
            )
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
