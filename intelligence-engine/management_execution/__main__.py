"""CLI: python -m management_execution --company TCS"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(
            "usage: python -m management_execution "
            "--health|--dashboard|--company TICKER|--timeline TICKER|"
            "--score TICKER|--objectives TICKER"
        )
        return 0

    cmd = args[0]

    def _need_ticker() -> str | None:
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return None
        return args[1]

    if cmd == "--health":
        from management_execution.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if cmd == "--dashboard":
        from management_execution.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if cmd == "--company":
        t = _need_ticker()
        if not t:
            return 2
        from management_execution.production import company

        print(json.dumps(company(t), indent=2, default=str))
        return 0
    if cmd == "--timeline":
        t = _need_ticker()
        if not t:
            return 2
        from management_execution.production import timeline

        print(json.dumps(timeline(t), indent=2, default=str))
        return 0
    if cmd == "--score":
        t = _need_ticker()
        if not t:
            return 2
        from management_execution.production import score

        print(json.dumps(score(t), indent=2, default=str))
        return 0
    if cmd == "--objectives":
        t = _need_ticker()
        if not t:
            return 2
        from management_execution.production import objectives

        print(json.dumps(objectives(t), indent=2, default=str))
        return 0

    if not cmd.startswith("--"):
        from management_execution.production import company

        print(json.dumps(company(cmd), indent=2, default=str))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
