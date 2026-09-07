"""CLI: python -m watchlist_office --watchlist Core --add Core TCS"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="watchlist_office", description="WO-01 Watchlist Office")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--create", metavar="NAME", help="Create watchlist")
    parser.add_argument("--watchlist", metavar="NAME", help="Watchlist Queue Report")
    parser.add_argument("--queue", metavar="NAME", help="Research queue only")
    parser.add_argument("--add", nargs=2, metavar=("WATCHLIST", "TICKER"), help="Add company")
    parser.add_argument("--remove", nargs=2, metavar=("WATCHLIST", "TICKER"), help="Remove company")
    parser.add_argument("--priority", default="Medium")
    parser.add_argument("--status", default="New")
    parser.add_argument("--list", action="store_true", dest="list_all")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from watchlist_office.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from watchlist_office.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.list_all:
        from watchlist_office import store as wl_store

        print(json.dumps(wl_store.list_watchlists(), indent=2, default=str))
        return 0
    if args.create:
        from watchlist_office.production import create

        print(json.dumps(create({"name": args.create}), indent=2, default=str))
        return 0
    if args.watchlist:
        from watchlist_office.production import get_watchlist

        print(json.dumps(get_watchlist(args.watchlist), indent=2, default=str))
        return 0
    if args.queue:
        from watchlist_office.production import get_queue

        print(json.dumps(get_queue(args.queue), indent=2, default=str))
        return 0
    if args.add:
        from watchlist_office.production import add

        print(
            json.dumps(
                add(args.add[0], {"ticker": args.add[1], "priority": args.priority, "status": args.status}),
                indent=2,
                default=str,
            )
        )
        return 0
    if args.remove:
        from watchlist_office.production import remove

        print(json.dumps(remove(args.remove[0], args.remove[1]), indent=2, default=str))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
