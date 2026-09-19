"""CLI: python -m institutional_benchmarks --list|--case|--sector|--run-all"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_benchmarks",
        description="AGI Institutional Benchmark Suite (IBS-01)",
    )
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_all")
    parser.add_argument("--case", metavar="CASE_ID", help="Run one benchmark case")
    parser.add_argument("--show", metavar="CASE_ID", help="Show case metadata")
    parser.add_argument("--sector", metavar="SECTOR", help="Run all cases in a sector")
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--historical-cutoff", metavar="YYYY-MM-DD")
    parser.add_argument("--inject-fixture-answers", action="store_true")
    parser.add_argument("--json-full", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_benchmarks.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from institutional_benchmarks.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.list_all:
        from institutional_benchmarks.production import list_benchmarks

        print(json.dumps(list_benchmarks(), indent=2, default=str))
        return 0
    if args.show:
        from institutional_benchmarks.production import get_benchmark

        print(
            json.dumps(
                get_benchmark(args.show, cutoff=args.historical_cutoff),
                indent=2,
                default=str,
            )
        )
        return 0

    cutoff = args.historical_cutoff
    fixture = {"forbidden": True} if args.inject_fixture_answers else None

    if args.case:
        from institutional_benchmarks.production import run

        result = run(args.case, cutoff=cutoff, fixture_answers=fixture)
        if args.json_full:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(
                json.dumps(
                    {
                        "case_id": result.get("case_id"),
                        "passed": result.get("passed"),
                        "score": result.get("research_quality_score"),
                        "failure_codes": result.get("failure_codes"),
                        "coverage_summary": result.get("coverage_summary"),
                        "historical_cutoff": result.get("historical_cutoff"),
                        "summary": (result.get("score") or {}).get("summary"),
                    },
                    indent=2,
                    default=str,
                )
            )
        return 0 if result.get("passed") else 1

    if args.sector:
        from institutional_benchmarks.production import run_sector_benchmarks

        result = run_sector_benchmarks(args.sector, cutoff=cutoff)
        print(
            json.dumps(
                {
                    "label": result.get("label"),
                    "cases_run": result.get("cases_run"),
                    "passed": result.get("passed"),
                    "failed": result.get("failed"),
                    "average_score": result.get("average_score"),
                    "release_gate": result.get("release_gate"),
                    "results": result.get("results"),
                },
                indent=2,
                default=str,
            )
        )
        return 0 if not (result.get("release_gate") or {}).get("blocked") else 1

    if args.run_all:
        from institutional_benchmarks.production import run_all_benchmarks

        result = run_all_benchmarks(cutoff=cutoff)
        print(
            json.dumps(
                {
                    "label": result.get("label"),
                    "cases_run": result.get("cases_run"),
                    "passed": result.get("passed"),
                    "failed": result.get("failed"),
                    "average_score": result.get("average_score"),
                    "hallucination_count": result.get("hallucination_count"),
                    "broken_provenance": result.get("broken_provenance"),
                    "unsupported_conclusions": result.get("unsupported_conclusions"),
                    "consistency_failures": result.get("consistency_failures"),
                    "release_gate": result.get("release_gate"),
                },
                indent=2,
                default=str,
            )
        )
        return 0 if not (result.get("release_gate") or {}).get("blocked") else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
