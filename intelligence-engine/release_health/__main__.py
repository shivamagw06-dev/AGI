"""CLI: python -m release_health --run|--dashboard|--health"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release_health", description="AGI Release Health (RH-01)")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--skip-unit-tests", action="store_true")
    parser.add_argument("--json-full", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from release_health.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard and not args.run:
        from release_health.production import dashboard

        print(json.dumps(dashboard(refresh=False), indent=2, default=str))
        return 0

    from release_health.production import run

    result = run({"run_unit_tests": not args.skip_unit_tests})
    if args.json_full:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(
            json.dumps(
                {
                    "title": result.get("title"),
                    "ready_for_release": result.get("ready_for_release_label"),
                    "ist": result.get("ist", {}).get("display"),
                    "ibs": result.get("ibs", {}).get("display"),
                    "e2e": result.get("e2e", {}).get("display"),
                    "average_benchmark": result.get("average_benchmark"),
                    "hallucinations": result.get("hallucinations"),
                    "broken_provenance": result.get("broken_provenance"),
                    "regression": result.get("regression"),
                    "performance": result.get("performance"),
                    "rows": result.get("rows"),
                    "elapsed_ms": result.get("elapsed_ms"),
                    "access": {
                        "admin_ui": "/admin/release-health",
                        "cli": "python3 -m release_health --run",
                    },
                },
                indent=2,
                default=str,
            )
        )
    return 0 if result.get("ready_for_release") else 1


if __name__ == "__main__":
    raise SystemExit(main())
