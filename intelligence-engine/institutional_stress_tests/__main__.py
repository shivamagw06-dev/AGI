"""CLI: python -m institutional_stress_tests --case IST-01|IST-02"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_stress_tests",
        description="AGI Institutional Stress Tests — IST-01 orchestration / IST-02 raw evidence",
    )
    parser.add_argument("--case", default="IST-01", help="Case id (IST-01 or IST-02)")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--run", action="store_true", help="Run selected case")
    parser.add_argument("--inventory", action="store_true", help="IST-01 probes only")
    parser.add_argument("--single-module", metavar="MODULE", help="IST-01 negative: one module only")
    parser.add_argument(
        "--inject-fixture-answers",
        action="store_true",
        help="IST-02 negative: inject fixture answers (must FAIL)",
    )
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--show-report", action="store_true", help="Print IST-02 institutional report sections")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_stress_tests.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from institutional_stress_tests.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.report:
        from institutional_stress_tests.production import report

        out = report(args.case)
        print(out.get("markdown") or json.dumps(out, indent=2, default=str))
        return 0 if out.get("passed") else 1

    case = str(args.case or "IST-01").upper()
    if args.run or args.inventory or args.single_module or args.inject_fixture_answers:
        from institutional_stress_tests.production import run

        if case in {"IST-02", "IST02"}:
            fixture = {"forbidden": True} if args.inject_fixture_answers else None
            result = run(case, fixture_answers=fixture, write_report=args.write_report)
            payload = {
                "case_id": result.get("case_id"),
                "passed": result.get("passed"),
                "research_quality_score": result.get("research_quality_score"),
                "failure_codes": result.get("failure_codes"),
                "coverage_summary": result.get("coverage_summary"),
                "confidence_summary": {
                    "confidence": (result.get("confidence_summary") or {}).get("confidence"),
                    "reason_confidence_cannot_be_higher": (result.get("confidence_summary") or {}).get(
                        "reason_confidence_cannot_be_higher"
                    ),
                },
                "summary": (result.get("score") or {}).get("summary"),
            }
            if args.show_report:
                report_obj = result.get("institutional_report") or {}
                sections = report_obj.get("sections") or {}
                payload["executive_summary"] = sections.get("executive_summary")
                payload["what_happened"] = sections.get("what_happened")
                payload["evidence_supporting"] = sections.get("evidence_supporting")
                payload["evidence_contradicting"] = sections.get("evidence_contradicting")
                payload["outstanding_unknowns"] = sections.get("outstanding_unknowns")
                payload["monitoring_framework"] = sections.get("monitoring_framework")
                payload["counterfactual_analysis"] = sections.get("counterfactual_analysis")
                payload["confidence_discussion"] = sections.get("confidence_discussion")
            print(json.dumps(payload, indent=2, default=str))
            return 0 if result.get("passed") else 1

        from institutional_stress_tests.fixtures import complete_answers, fire_prebuilt

        prebuilt = fire_prebuilt() if (args.run or args.single_module) else None
        answers = complete_answers() if args.run else None
        modules_filter = [args.single_module] if args.single_module else None
        result = run(
            case,
            prebuilt=prebuilt,
            answers=answers,
            modules_filter=modules_filter,
            write_report=args.write_report,
        )
        print(
            json.dumps(
                {
                    "case_id": result.get("case_id"),
                    "passed": result.get("passed"),
                    "score": (result.get("score") or {}).get("weighted_total"),
                    "automatic_failures": (result.get("score") or {}).get("automatic_failures"),
                    "gates": (result.get("score") or {}).get("gates"),
                    "orchestration": (result.get("score") or {}).get("orchestration"),
                    "summary": (result.get("score") or {}).get("summary"),
                    "report_paths": result.get("report_paths"),
                },
                indent=2,
                default=str,
            )
        )
        return 0 if result.get("passed") else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
