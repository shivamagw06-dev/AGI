"""CLI: python -m institutional_observation --ticker AXISBANK"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_observation",
        description="IO-01 Institutional Observation Engine (proactive, deterministic, no LLM)",
    )
    parser.add_argument("--ticker", required=False)
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--critical-only", action="store_true")
    parser.add_argument(
        "--inject",
        default="",
        help="Optional event key: quarterly_results|rbi_repo_cut|ceo_resignation|share_split|forecast_revision",
    )
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_observation.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    ticker = (args.ticker or "").strip()
    if not ticker:
        parser.error("--ticker is required unless --health")

    from institutional_observation.production import observe_company

    events = None
    if args.inject:
        key = args.inject.strip().lower()
        events = [
            {
                "key": key,
                "detail": f"Injected institutional event: {key}",
                "magnitude": 1.0,
            }
        ]

    # Establish baseline silently, then observe (with optional inject)
    observe_company(ticker)
    result = observe_company(
        ticker,
        critical_only=bool(args.critical_only),
        include_decision_changes=True,
        force_events=events,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Observation cycle rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    print("Observations")
    print()
    rows = result.get("observations") or []
    if not rows:
        print("(none — silent update or no material change)")
        print()
    for o in rows:
        print(f"{o.get('category')}  [{o.get('severity')}]  conf={o.get('confidence')}")
        print(o.get("summary"))
        print()

    print("Severity")
    print()
    if rows:
        print(rows[0].get("severity"))
    else:
        print((result.get("significance") or {}).get("severity") or "ignore")
    print()

    print("Affected Decisions")
    print()
    for o in rows:
        for d in o.get("affected_decisions") or []:
            print(f"- {d}")
        if o.get("decision_changed"):
            print(f"- {o.get('previous_decision')} → {o.get('current_decision')}")
    if not rows:
        print("(none)")
    print()

    print("Recommended Actions")
    print()
    for o in rows:
        print(f"- {o.get('recommended_action')}")
    if not rows:
        plan = result.get("plan") or {}
        print(f"- {plan.get('recommended_action') or 'No action'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
