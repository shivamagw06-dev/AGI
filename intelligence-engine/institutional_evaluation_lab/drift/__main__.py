"""CLI — recommendation drift between Evaluation Lab releases.

Examples:
  python -m institutional_evaluation_lab.drift --previous PR306 --current PR307
  python -m institutional_evaluation_lab.drift --previous PR306 --current PR308 --json
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGIB Recommendation Drift (PR #308)")
    parser.add_argument("--previous", required=True, help="Previous release id")
    parser.add_argument("--current", required=True, help="Current release id")
    parser.add_argument("--governance-failures", type=int, default=None)
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    from institutional_evaluation_lab.drift.production import compare_releases

    report = compare_releases(
        previous_release=args.previous,
        current_release=args.current,
        governance_failures=args.governance_failures,
        persist=not args.no_persist,
    )
    if report.get("error"):
        print(json.dumps(report, indent=2))
        return 2

    if args.json:
        light = {k: v for k, v in report.items() if k not in {"rows", "changed_rows"}}
        light["changed_sample"] = (report.get("changed_rows") or [])[:20]
        print(json.dumps(light, indent=2, default=str))
    else:
        print(report.get("release_notes_text") or "")
        print("")
        print(f"Budget passed: {report.get('budget', {}).get('passed')}")
        print(f"Requires review: {(report.get('review_queue') or {}).get('requires_review')}")
        print(f"By reason: {report.get('by_reason_code')}")
        if report.get("report_path"):
            print(f"Report: {report['report_path']}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
