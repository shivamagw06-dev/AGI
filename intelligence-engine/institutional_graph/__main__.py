"""CLI: python -m institutional_graph --ticker AXISBANK"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_graph",
        description="KG-01 Institutional Knowledge Graph (single-company, deterministic, no LLM)",
    )
    parser.add_argument("--ticker", required=False)
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-paths", action="store_true")
    parser.add_argument("--no-inference", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_graph.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    ticker = (args.ticker or "").strip()
    if not ticker:
        parser.error("--ticker is required unless --health")

    from institutional_graph.production import get_company_graph

    result = get_company_graph(
        ticker,
        include_paths=bool(args.include_paths),
        include_inference=not args.no_inference,
        rebuild=True,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Knowledge graph rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    print("Entity Summary")
    print()
    print(f"entities: {result.get('entity_count')}")
    by_type: dict[str, int] = {}
    for n in result.get("nodes") or []:
        by_type[n.get("type") or "?"] = by_type.get(n.get("type") or "?", 0) + 1
    for typ, count in sorted(by_type.items()):
        print(f"- {typ}: {count}")
    print()
    print("Relationship Summary")
    print()
    print(f"relationships: {result.get('relationship_count')}")
    print(f"inferred: {result.get('inference_count')}")
    print()
    print("Decision Graph")
    print()
    diag = result.get("diagnostics") or {}
    for step in diag.get("decision_chain") or []:
        # resolve label
        label = step
        for n in result.get("nodes") or []:
            if n.get("id") == step:
                label = f"{n.get('type')}: {n.get('label')}"
                break
        print(f"- {label}")
    print()
    print("Impact Scores")
    print()
    impact = result.get("impact") or {}
    for key in (
        "Business Quality",
        "Financial Quality",
        "Valuation",
        "Macro",
        "Risk",
        "Governance",
    ):
        pts = impact.get(key, 0)
        sign = f"+{pts}" if isinstance(pts, int) and pts > 0 else str(pts)
        print(f"{key}: {sign}")
    print()
    print("Inference Paths")
    print()
    for rid in (result.get("inferred_relationship_ids") or [])[:12]:
        rel = next((r for r in (result.get("relationships") or []) if r.get("id") == rid), None)
        if rel:
            print(f"- {rel.get('label')} ({rel.get('kind')}, strength={rel.get('strength')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
