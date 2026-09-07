"""CLI: python -m institutional_portfolio [--portfolio-id agi-core-equity]"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_portfolio",
        description=(
            "PKG-01 / PO-01 Portfolio Knowledge Graph — "
            "Portfolio → Companies → Relationships (deterministic, no LLM)"
        ),
    )
    parser.add_argument("--portfolio-id", default="agi-core-equity")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_portfolio.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_portfolio.production import get_portfolio_graph

    result = get_portfolio_graph(args.portfolio_id, rebuild=True, include_company_graphs=True)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Portfolio graph rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    print("Institutional Portfolio")
    print()
    port = result.get("portfolio") or {}
    print(f"{port.get('name')}  ({port.get('portfolio_id')})")
    print(f"holdings: {port.get('holding_count')}  cash: {float(port.get('cash_weight') or 0):.1%}")
    print()

    print("Holdings")
    print()
    for h in result.get("holdings") or []:
        print(
            f"- {h.get('ticker'):12} {float(h.get('weight') or 0):6.1%}  "
            f"{h.get('recommendation') or '—':4}  conf={h.get('confidence') or '—'}"
        )
    print()

    print("Exposures (sector)")
    print()
    for e in result.get("exposures") or []:
        if e.get("dimension") == "sector":
            print(f"- {e.get('name')}: {float(e.get('weight') or 0):.1%}")
    print()

    print("Concentration")
    print()
    conc = result.get("concentration") or {}
    print(f"HHI: {conc.get('hhi')}")
    print(f"Top 5: {float(conc.get('top_5_weight') or 0):.1%}")
    largest = conc.get("largest_position") or {}
    if largest:
        print(f"Largest: {largest.get('ticker')} {float(largest.get('weight') or 0):.1%}")
    print()

    print("Correlations")
    print()
    corr = result.get("correlations") or {}
    print(f"average ρ (proxy): {corr.get('average')}")
    print(f"pairs: {corr.get('count')}")
    print()

    print("Graph")
    print()
    print(f"entities: {result.get('entity_count')}")
    print(f"relationships: {result.get('relationship_count')}")
    print("lineage:", " → ".join(result.get("lineage") or []))
    print()

    print("Risks")
    print()
    risks = result.get("risks") or []
    if not risks:
        print("(none above threshold)")
    for r in risks:
        print(f"- [{r.get('severity')}] {r.get('label')}: {r.get('detail')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
