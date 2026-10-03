"""CLI: python -m comparative_intelligence --compare TCS INFY"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="comparative_intelligence",
        description="CIO-01 Comparative Intelligence Office — side-by-side FIRE comparison",
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="TICKER",
        help="Compare two or more tickers",
    )
    parser.add_argument("--question", metavar="TEXT", help="Natural-language comparison question")
    parser.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Explicit tickers for --question",
    )
    parser.add_argument("--type", dest="comparison_type", metavar="TYPE", help="Comparison type override")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from comparative_intelligence.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from comparative_intelligence.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.metrics:
        from comparative_intelligence import store as cio_store

        print(json.dumps(cio_store.metrics(), indent=2, default=str))
        return 0

    if args.compare:
        from comparative_intelligence.production import compare_companies

        if len(args.compare) < 2:
            print("at least two tickers required for --compare", file=sys.stderr)
            return 2
        print(
            json.dumps(
                compare_companies(args.compare, comparison_type=args.comparison_type),
                indent=2,
                default=str,
            )
        )
        return 0

    if args.question:
        from comparative_intelligence.production import query
        from comparative_intelligence.routing import extract_tickers

        tickers = list(args.tickers or extract_tickers(args.question))
        if len(tickers) < 2:
            print(
                "could not resolve two tickers; pass --tickers A B",
                file=sys.stderr,
            )
            return 2
        print(
            json.dumps(
                query(
                    tickers=tickers,
                    question=args.question,
                    comparison_type=args.comparison_type,
                ),
                indent=2,
                default=str,
            )
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
