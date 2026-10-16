"""CLI: python -m institutional_portfolio_decision --portfolio default"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_portfolio_decision",
        description=(
            "CIO-01 Institutional Portfolio Decision System — "
            "deterministic portfolio actions; company decisions are referential inputs"
        ),
    )
    parser.add_argument("--portfolio", "--portfolio-id", dest="portfolio", default="default")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_portfolio_decision.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_portfolio_decision.production import decide_portfolio

    result = decide_portfolio({"portfolio_id": args.portfolio})
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Portfolio decision rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    d = result["decision"]
    print("Recommendation")
    print()
    print(d.get("recommendation"))
    print()
    print("Confidence")
    print()
    print(d.get("confidence"))
    print(f"Conviction: {d.get('conviction')}  Posture: {d.get('investment_posture')}")
    print()
    print("Allocation Actions")
    print()
    actions = d.get("allocation_actions") or []
    if not actions:
        print("(none)")
    for a in actions:
        print(
            f"- {a.get('ticker')}: {float(a.get('from_weight') or 0):.0%} → "
            f"{float(a.get('to_weight') or 0):.0%}  ({a.get('reason')})"
        )
    print()
    print("Exposure Actions")
    print()
    for a in d.get("exposure_actions") or []:
        print(
            f"- [{a.get('action')}] {a.get('dimension')}/{a.get('name')}: "
            f"{float(a.get('from_weight') or 0):.0%} → {float(a.get('to_weight') or 0):.0%} "
            f"— {a.get('reason')}"
        )
    print()
    print("Monitoring")
    print()
    plan = d.get("monitoring_plan") or {}
    for item in plan.get("required_reviews") or []:
        print(f"- {item}")
    for item in plan.get("committee_items") or []:
        print(f"- {item}")
    if not (plan.get("required_reviews") or plan.get("committee_items")):
        for item in (d.get("monitoring_items") or [])[:8]:
            print(f"- {item}")
    print()
    print("Diagnostics")
    print()
    diag = result.get("diagnostics") or {}
    print(f"rule_path: {diag.get('rule_path') or d.get('rule_path')}")
    print(f"lineage: {' → '.join(d.get('lineage') or [])}")
    print(f"mutates_company_decisions: {d.get('mutates_company_decisions')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
