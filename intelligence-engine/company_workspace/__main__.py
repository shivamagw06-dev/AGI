"""CLI: python -m company_workspace --company TCS"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="company_workspace", description="CW-01 Company Workspace")
    parser.add_argument("--company", "--ticker", dest="company", metavar="TICKER", help="Assemble workspace")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--timeline", metavar="TICKER", help="Unified timeline")
    parser.add_argument("--research", metavar="TICKER", help="Research history")
    parser.add_argument("--evidence", metavar="TICKER", help="Evidence references")
    parser.add_argument("--search", nargs=2, metavar=("TICKER", "QUERY"), help="Search workspace")
    parser.add_argument("--scope", default="all", help="Search scope: all|section|evidence|timeline")
    parser.add_argument("--prebuilt", metavar="JSON", help="Path to prebuilt FIRE/IO module JSON map")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    prebuilt = None
    if args.prebuilt:
        with open(args.prebuilt, encoding="utf-8") as fh:
            prebuilt = json.load(fh)

    if args.health:
        from company_workspace.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from company_workspace.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.timeline:
        from company_workspace.production import timeline

        print(json.dumps(timeline(args.timeline), indent=2, default=str))
        return 0
    if args.research:
        from company_workspace.production import research

        print(json.dumps(research(args.research), indent=2, default=str))
        return 0
    if args.evidence:
        from company_workspace.production import evidence

        print(json.dumps(evidence(args.evidence), indent=2, default=str))
        return 0
    if args.search:
        from company_workspace.production import search

        print(json.dumps(search(args.search[0], args.search[1], scope=args.scope), indent=2, default=str))
        return 0
    if args.company:
        from company_workspace.production import workspace

        print(
            json.dumps(
                workspace(args.company, prebuilt=prebuilt, use_cache=not args.no_cache),
                indent=2,
                default=str,
            )
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
