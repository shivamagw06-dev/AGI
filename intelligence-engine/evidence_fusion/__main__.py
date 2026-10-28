"""CLI: python -m evidence_fusion --company TCS"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(
            "usage: python -m evidence_fusion "
            "--health|--dashboard|--company TICKER|--supported TICKER|"
            "--conflicts TICKER|--alignment TICKER"
        )
        return 0

    cmd = args[0]

    def _need_ticker() -> str | None:
        if len(args) < 2:
            print("ticker required", file=sys.stderr)
            return None
        return args[1]

    if cmd == "--health":
        from evidence_fusion.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if cmd == "--dashboard":
        from evidence_fusion.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if cmd == "--company":
        t = _need_ticker()
        if not t:
            return 2
        from evidence_fusion.production import company

        print(json.dumps(company(t), indent=2, default=str))
        return 0
    if cmd == "--supported":
        t = _need_ticker()
        if not t:
            return 2
        from evidence_fusion.production import supported

        print(json.dumps(supported(t), indent=2, default=str))
        return 0
    if cmd == "--conflicts":
        t = _need_ticker()
        if not t:
            return 2
        from evidence_fusion.production import conflicts

        print(json.dumps(conflicts(t), indent=2, default=str))
        return 0
    if cmd == "--alignment":
        t = _need_ticker()
        if not t:
            return 2
        from evidence_fusion.production import alignment

        print(json.dumps(alignment(t), indent=2, default=str))
        return 0

    if not cmd.startswith("--"):
        from evidence_fusion.production import company

        print(json.dumps(company(cmd), indent=2, default=str))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
