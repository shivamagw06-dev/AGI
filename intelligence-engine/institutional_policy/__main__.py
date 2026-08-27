"""CLI: python -m institutional_policy --portfolio default --policy family_office"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_policy",
        description=(
            "PCE-01 Institutional Policy & Constraint Engine — "
            "deterministic mandate compliance for the Investment Office"
        ),
    )
    parser.add_argument("--portfolio", "--portfolio-id", dest="portfolio", default="default")
    parser.add_argument("--policy", "--profile", dest="policy", default="family_office")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_policy.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_policy.production import check_policy

    result = check_policy({"portfolio_id": args.portfolio, "policy": args.policy})
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Policy check rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    a = result["assessment"]
    print("Compliance")
    print()
    print(a.get("overall_status"))
    print(f"Score: {a.get('compliance_score')}  Profile: {a.get('profile_id')}")
    print()
    print("Violations")
    print()
    viols = a.get("violations") or []
    if not viols:
        print("(none)")
    for v in viols:
        print(f"- [{v.get('severity')}] {v.get('name')}: {v.get('detail')}")
        print(f"  Action: {v.get('required_action')}")
    print()
    print("Required actions")
    print()
    actions = a.get("required_actions") or []
    if not actions:
        print("(none)")
    for act in actions:
        print(f"- {act}")
    print()
    print(f"Passed: {a.get('passed_count')}  Failed: {a.get('failed_count')}")
    print(f"policy_id: {a.get('policy_id')}")
    print(f"lineage: {' → '.join(a.get('lineage') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
