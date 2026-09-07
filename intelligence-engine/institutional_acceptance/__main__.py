"""CLI: python -m institutional_acceptance"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGIB PAT-01 Production Acceptance Test")
    parser.add_argument("--mode", default="harness", choices=["harness", "live"])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--no-stress", action="store_true")
    args = parser.parse_args(argv)

    from institutional_acceptance.test_runner import run_all

    report = run_all(mode=args.mode, include_stress=not args.no_stress)
    if args.as_json:
        print(json.dumps(report, indent=2, default=str))
    elif not args.quiet:
        print(report.get("report_text") or report.get("overall_result"))
        print()
        print(f"Cases: {report.get('passed')}/{report.get('total')} PASS")
        print(f"Result: {report.get('overall_result')}")
    else:
        print("PASS" if report.get("certified") else "FAIL")

    return 0 if report.get("certified") else 1


if __name__ == "__main__":
    sys.exit(main())
