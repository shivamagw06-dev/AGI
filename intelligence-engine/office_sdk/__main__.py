"""CLI: python -m office_sdk --catalog|--domains|--health|--invoke '{...}'"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="office_sdk", description="Shared Office SDK")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--domains", action="store_true")
    parser.add_argument("--invoke", metavar="JSON", help="Dispatch OfficeRequest JSON")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from office_sdk.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from office_sdk.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.catalog:
        from office_sdk.production import office_catalog

        print(json.dumps(office_catalog(), indent=2, default=str))
        return 0
    if args.domains:
        from office_sdk.production import domains

        print(json.dumps(domains(), indent=2, default=str))
        return 0
    if args.invoke:
        from office_sdk.production import invoke

        req = json.loads(args.invoke)
        print(json.dumps(invoke(req), indent=2, default=str))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
