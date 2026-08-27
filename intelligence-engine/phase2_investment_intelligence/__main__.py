"""CLI: python -m phase2_investment_intelligence"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AGIB Phase 2 Investment Intelligence Programme")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    from phase2_investment_intelligence.production import programme

    pack = programme()
    if args.json:
        print(json.dumps(pack, indent=2, default=str))
    else:
        print(f"{pack['programme']}  {pack['version']}")
        print(f"Baseline: {pack['baseline']['name']}  [{pack['baseline']['status']}]")
        print(f"Objective: {pack['primary_objective']}")
        print()
        print("Workstreams (implementation order):")
        for wid in pack["workstreams"]["implementation_order"]:
            ws = next(w for w in pack["workstreams"]["workstreams"] if w["id"] == wid)
            print(f"  {wid}  {ws['title']}  [{ws['status']}]")
        print()
        print(f"Doc: {pack['doc']}")
        print("Recommended first build:", ", ".join(pack["workstreams"]["recommended_first_build"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
