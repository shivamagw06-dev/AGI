"""CLI: python -m product_experience_validation [--run|--health|--dashboard|--workflow WF1]"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="product_experience_validation",
        description="E2E-01 — AGI Institutional Product Experience Validation",
    )
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--workflow", metavar="WFn")
    parser.add_argument("--json-full", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from product_experience_validation.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if args.dashboard:
        from product_experience_validation.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if args.report:
        from product_experience_validation.production import report

        print(json.dumps(report(), indent=2, default=str))
        return 0
    if args.workflow:
        from product_experience_validation.production import run

        out = run({"workflow": args.workflow})
        print(json.dumps(out, indent=2, default=str))
        return 0

    # default: run
    from product_experience_validation.production import run

    result = run({})
    if args.json_full:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(
            json.dumps(
                {
                    "workstream_id": result.get("workstream_id"),
                    "passed": result.get("passed"),
                    "score": result.get("score"),
                    "pass_score": result.get("pass_score"),
                    "failure_codes": result.get("failure_codes"),
                    "final_answer": result.get("final_answer"),
                    "institutionally_ready": result.get("institutionally_ready"),
                    "summary": result.get("summary"),
                    "dimensions": {
                        k: v.get("points") for k, v in (result.get("dimensions") or {}).items()
                    },
                    "elapsed_ms": result.get("elapsed_ms"),
                },
                indent=2,
                default=str,
            )
        )
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
