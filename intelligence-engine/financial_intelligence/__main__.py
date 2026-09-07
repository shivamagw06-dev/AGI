"""CLI: python -m financial_intelligence --financial-intelligence TCS"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(
            "usage: python -m financial_intelligence "
            "--health|--dashboard|--financial-intelligence TICKER|--financial-findings TICKER|"
            "--financial-drivers TICKER|--financial-relationships TICKER"
        )
        return 0

    cmd = args[0]
    if cmd == "--health":
        from financial_intelligence.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if cmd == "--dashboard":
        from financial_intelligence.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if cmd == "--financial-intelligence":
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        from financial_intelligence.production import company

        print(json.dumps(company(args[1]), indent=2, default=str))
        return 0
    if cmd == "--financial-findings":
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        from financial_intelligence.production import findings

        print(json.dumps(findings(args[1]), indent=2, default=str))
        return 0
    if cmd == "--financial-drivers":
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        from financial_intelligence.production import financial_drivers

        print(json.dumps(financial_drivers(args[1]), indent=2, default=str))
        return 0
    if cmd == "--financial-relationships":
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return 2
        from financial_intelligence.production import financial_relationships

        print(json.dumps(financial_relationships(args[1]), indent=2, default=str))
        return 0

    # Bare ticker → full report
    if not cmd.startswith("--"):
        from financial_intelligence.production import company

        print(json.dumps(company(cmd), indent=2, default=str))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
