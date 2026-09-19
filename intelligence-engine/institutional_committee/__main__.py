"""CLI: python -m institutional_committee --portfolio default"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_committee",
        description=(
            "ICE-01 Investment Committee Engine — "
            "deterministic governance of CIO portfolio decisions"
        ),
    )
    parser.add_argument("--portfolio", "--portfolio-id", dest="portfolio", default="default")
    parser.add_argument("--policy", dest="policy", default="family_office")
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_committee.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    if args.pending:
        from institutional_committee.production import get_pending

        result = get_pending()
        print(json.dumps(result, indent=2, default=str))
        return 0

    from institutional_committee.production import review_committee

    result = review_committee({"portfolio_id": args.portfolio, "policy": args.policy})
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Committee review rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    r = result["resolution"]
    print("Resolution")
    print()
    print(r.get("status"))
    print(r.get("outcome"))
    print()
    print("Votes")
    print()
    for v in r.get("votes") or []:
        print(f"- {v.get('desk')}: {v.get('vote')} — {v.get('rationale')}")
    print()
    print("Action items")
    print()
    actions = r.get("required_actions") or []
    if not actions:
        print("(none)")
    for a in actions:
        print(f"- {a.get('title')}: {a.get('detail')}")
        print(f"  Owner: {a.get('owner')}  Due: {a.get('due')}")
    print()
    print("Follow-up")
    print()
    for f in r.get("follow_up_items") or []:
        print(f"- {f}")
    print(f"Review date: {r.get('review_date')}")
    print(f"resolution_id: {r.get('resolution_id')}")
    print(f"lineage: {' → '.join(r.get('lineage') or [])}")
    print(f"mutates_upstream: {r.get('mutates_upstream')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
