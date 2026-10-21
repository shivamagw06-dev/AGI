"""CLI: python -m business_intelligence --company TCS"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(
            "usage: python -m business_intelligence "
            "--health|--dashboard|--company TICKER|--segments TICKER|"
            "--strategy TICKER|--risks TICKER|--guidance TICKER"
        )
        return 0

    cmd = args[0]

    def _need_ticker() -> str | None:
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return None
        return args[1]

    if cmd == "--health":
        from business_intelligence.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if cmd == "--dashboard":
        from business_intelligence.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if cmd == "--company":
        t = _need_ticker()
        if not t:
            return 2
        from business_intelligence.production import company

        print(json.dumps(company(t), indent=2, default=str))
        return 0
    if cmd == "--segments":
        t = _need_ticker()
        if not t:
            return 2
        from business_intelligence.production import segments

        print(json.dumps(segments(t), indent=2, default=str))
        return 0
    if cmd == "--strategy":
        t = _need_ticker()
        if not t:
            return 2
        from business_intelligence.production import strategy

        print(json.dumps(strategy(t), indent=2, default=str))
        return 0
    if cmd == "--risks":
        t = _need_ticker()
        if not t:
            return 2
        from business_intelligence.production import risks

        print(json.dumps(risks(t), indent=2, default=str))
        return 0
    if cmd == "--guidance":
        t = _need_ticker()
        if not t:
            return 2
        from business_intelligence.production import guidance

        print(json.dumps(guidance(t), indent=2, default=str))
        return 0

    # Bare ticker → full company pack
    if not cmd.startswith("--"):
        from business_intelligence.production import company

        print(json.dumps(company(cmd), indent=2, default=str))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
