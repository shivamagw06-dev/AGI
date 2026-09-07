"""CLI: python -m committee_certification_v2 [--runs N] [--max-peers N]."""

from __future__ import annotations

import argparse
import json
import sys

from committee_certification_v2.production import health, run_certification


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AGIB IC-10 Committee Certification v2.0")
    p.add_argument("--runs", type=int, default=3, help="Robustness consecutive executions")
    p.add_argument("--max-peers", type=int, default=3)
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-persist", action="store_true")
    p.add_argument("--json", action="store_true", help="Print full JSON instead of markdown")
    args = p.parse_args(argv)

    if args.runs == 0:
        print(json.dumps(health(), indent=2))
        return 0

    result = run_certification(
        robustness_runs=max(1, args.runs),
        force=args.force,
        max_peers=max(1, min(args.max_peers, 8)),
        persist=not args.no_persist,
    )
    if args.json:
        body = {k: v for k, v in result.items() if k != "markdown"}
        print(json.dumps(body, indent=2, default=str))
    else:
        print(result.get("markdown") or json.dumps(result.get("aggregate"), indent=2))
        print(
            f"\n# Score: {result['aggregate']['total_score']}/100 — {result['aggregate']['grade']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
