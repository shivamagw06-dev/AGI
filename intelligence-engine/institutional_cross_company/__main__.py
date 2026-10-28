"""CLI: python -m institutional_cross_company --company HDFCBANK"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_cross_company",
        description="CCI-01 Cross-Company Intelligence — relationship reasoning over KG-01",
    )
    parser.add_argument("--company", "--ticker", dest="company", default="")
    parser.add_argument("--sector", default="")
    parser.add_argument("--macro", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_cross_company.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_cross_company.production import (
        get_company_relationships,
        get_macro_relationships,
        get_sector_relationships,
        query_relationships,
    )

    if args.query:
        result = query_relationships({"question": args.query})
    elif args.macro:
        result = get_macro_relationships(args.macro)
    elif args.sector:
        result = get_sector_relationships(args.sector)
    else:
        result = get_company_relationships(args.company or "HDFCBANK")

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("CCI unavailable", file=sys.stderr)
        return 1

    print(f"CCI-01 · graph SoR: {result.get('kg_ref', {}).get('system', 'KG-01')}")
    print(f"owns_graph: {result.get('owns_graph', False)}")
    print()
    if result.get("competitors"):
        print("Competitors")
        for c in result["competitors"][:8]:
            print(f"- {c}")
        print()
    if result.get("macro_drivers"):
        print("Macro drivers")
        for m in result["macro_drivers"][:8]:
            print(f"- {m}")
        print()
    if result.get("propagation"):
        prop = result["propagation"]
        print("Propagation")
        print(" → ".join(prop.get("steps") or []))
        print(f"Affected: {len(prop.get('affected_entities') or [])}")
        print()
    print(f"Relationships: {len(result.get('relationships') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
