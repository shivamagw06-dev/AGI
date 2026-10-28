"""CLI: python -m institutional_grade_benchmark"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGIB IB-01 Institutional Benchmark")
    parser.add_argument("--mode", default="harness", choices=["harness", "live"])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    from institutional_grade_benchmark.runner import run_all

    report = run_all(mode=args.mode)
    if args.as_json:
        print(json.dumps(report, indent=2, default=str))
    elif not args.quiet:
        print(report.get("report_text") or "")
        print()
        print(f"Overall: {report.get('total_score')}/{report.get('total_max')}")
        print(f"Result: {report.get('overall_result')}")
        if report.get("provisional"):
            print(f"Note: {report.get('grade_reason')}")
    else:
        print("PASS" if report.get("institutional_grade") else "FAIL")

    return 0 if report.get("institutional_grade") else 1


if __name__ == "__main__":
    sys.exit(main())
