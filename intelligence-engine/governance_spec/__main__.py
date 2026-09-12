"""CLI — Phase 6 governance assertions against Evaluation Lab results.

Examples:
  python -m governance_spec --release PR306
  python -m governance_spec --spec
  python -m governance_spec --release PR306 --json
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AGIB Governance Spec — Phase 6 assertions (GOV-001…)"
    )
    parser.add_argument("--release", default=None, help="Evaluation Lab release id (results/{release})")
    parser.add_argument("--spec", action="store_true", help="Print Governance Spec v1.0 board only")
    parser.add_argument("--spec-version", default="v1.0")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.spec or not args.release:
        from governance_spec.v1_0.rules import spec_board

        board = spec_board()
        if args.json:
            print(json.dumps(board, indent=2))
        else:
            print(f"Governance Spec {board['spec_version']} (frozen={board['frozen']})")
            print("")
            for r in board["rules"]:
                print(f"{r['rule_id']}  [{r['severity']}]")
                print(f"  {r['assertion']}")
            print("")
            print(" → ".join(board["architecture"]))
        return 0 if args.spec or not args.release else 2

    from governance_spec.phase6 import format_board, run_phase6

    report = run_phase6(
        release_id=args.release,
        spec_version=args.spec_version,
        limit=args.limit,
    )
    if report.get("error"):
        print(json.dumps(report, indent=2))
        return 2
    if args.json:
        light = {k: v for k, v in report.items() if k != "ticker_results"}
        light["ticker_results_sample"] = (report.get("ticker_results") or [])[:10]
        print(json.dumps(light, indent=2, default=str))
    else:
        print(format_board(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
