"""CLI: python -m institutional_orchestrator --query 'Why reduce HDFCBANK?'"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_orchestrator",
        description=(
            "UAG-01 Universal Ask AGI — orchestrates registered institutional objects; "
            "does not generate investment recommendations"
        ),
    )
    parser.add_argument("--query", "-q", dest="query", default="")
    parser.add_argument("--portfolio", default="agi-core-equity")
    parser.add_argument("--policy", default="family_office")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--registry", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_orchestrator.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    if args.registry:
        from institutional_orchestrator.object_registry import catalog

        print(json.dumps(catalog(), indent=2, default=str))
        return 0

    if not args.query:
        parser.error("--query is required")

    from institutional_orchestrator.production import ask

    result = ask(
        {
            "question": args.query,
            "portfolio_id": args.portfolio,
            "policy": args.policy,
        }
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Ask rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    r = result["response"]
    print("Direct Answer")
    print()
    print(r.get("direct_answer"))
    print()
    print("Why")
    print()
    for line in r.get("why") or []:
        print(f"- {line}")
    print()
    print("Evidence lineage")
    print()
    print(" → ".join(r.get("evidence_lineage") or []))
    print()
    print("Objects consulted")
    print()
    print(", ".join(r.get("objects_consulted") or []) or "(none)")
    print()
    print(f"Intent: {r.get('intent')}  Confidence: {r.get('confidence')}")
    print(f"query_id: {r.get('query_id')}")
    print(f"generates_recommendations: {r.get('generates_recommendations')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
