"""CLI: python -m institutional_forecasting --ticker AXISBANK --scenario bull"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_forecasting",
        description="FG-01 Forecast & Scenario Graph (deterministic, no ML/LLM)",
    )
    parser.add_argument("--ticker", required=False)
    parser.add_argument("--scenario", default="bull", help="base|bull|bear|stress|optimistic|all")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-graph", action="store_true")
    parser.add_argument("--include-propagation", action="store_true", default=True)
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_forecasting.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    ticker = (args.ticker or "").strip()
    if not ticker:
        parser.error("--ticker is required unless --health")

    from institutional_forecasting.production import run_company_scenarios

    name = str(args.scenario or "bull").strip().lower()
    if name == "all":
        scenarios = ["base", "bull", "bear", "stress"]
    else:
        scenarios = [name]

    result = run_company_scenarios(
        ticker,
        scenarios=scenarios,
        include_graph=bool(args.include_graph),
        include_propagation=True,
        include_sensitivity=True,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Forecast scenarios rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    print("Scenario")
    print()
    for row in result.get("scenarios") or []:
        print(f"{row.get('scenario_name')}  p={row.get('probability')}")
        print()
        print("Decision")
        print()
        print(row.get("resulting_decision"))
        print()
        print("Confidence")
        print()
        print(row.get("resulting_confidence"))
        print()
        print("Propagation")
        print()
        for step in (row.get("graph_changes") or [])[:10]:
            print(f"- {step}")
        print()
        if row.get("reason_changes"):
            print("Decision evolution")
            print()
            for step in row.get("reason_changes") or []:
                print(f"- {step}")
            print()

    sens = result.get("sensitivity") or {}
    scorecard = sens.get("scorecard") or {}
    if scorecard:
        print("Sensitivity")
        print()
        for k, v in scorecard.items():
            sign = f"+{v}" if isinstance(v, int) and v > 0 else str(v)
            print(f"{k}: {sign}")
        print()

    print("Comparison")
    print()
    for c in result.get("comparison") or []:
        print(
            f"{c.get('scenario')}: {c.get('decision')}  {c.get('confidence')}%  (p={c.get('probability')})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
