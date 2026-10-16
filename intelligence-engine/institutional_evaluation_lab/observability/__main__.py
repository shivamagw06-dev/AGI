"""CLI — release observability dashboard (PR #309).

Examples:
  python -m institutional_evaluation_lab.observability --release PR308
  python -m institutional_evaluation_lab.observability --release PR308 --history PR306,PR307
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGIB Release Observability (PR #309)")
    parser.add_argument("--release", required=True)
    parser.add_argument("--history", default="", help="Comma-separated prior release ids")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    from institutional_evaluation_lab.observability.production import build_release_dashboard

    history = [x.strip() for x in args.history.split(",") if x.strip()]
    pack = build_release_dashboard(
        args.release,
        previous_releases=history or None,
        persist=not args.no_persist,
    )
    if not pack.get("found"):
        print(json.dumps(pack, indent=2))
        return 2
    if args.json:
        light = {k: v for k, v in pack.items() if k != "text"}
        print(json.dumps(light, indent=2, default=str))
    else:
        print(pack.get("text") or "")
        if pack.get("markdown_path"):
            print(f"\nWrote {pack['markdown_path']}")
    return 0 if (pack.get("executive") or {}).get("status") != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
