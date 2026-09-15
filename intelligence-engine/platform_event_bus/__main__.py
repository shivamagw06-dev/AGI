"""CLI: python -m platform_event_bus --statistics|--events|--types|--health"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="platform_event_bus", description="PEB-01 Platform Event Bus")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--statistics", action="store_true")
    parser.add_argument("--events", action="store_true")
    parser.add_argument("--types", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from platform_event_bus.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from platform_event_bus.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.statistics:
        from platform_event_bus.production import statistics

        print(json.dumps(statistics(), indent=2, default=str))
        return 0
    if args.events:
        from platform_event_bus.production import list_events

        print(json.dumps(list_events(limit=args.limit), indent=2, default=str))
        return 0
    if args.types:
        from platform_event_bus.production import list_types

        print(json.dumps(list_types(), indent=2, default=str))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
