"""CLI: python -m institutional_workspace --company AXISBANK"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_workspace",
        description="RW-01 Institutional Research Workspace — analyst workstation over linked objects",
    )
    parser.add_argument("--company", "--ticker", dest="company", default="")
    parser.add_argument("--portfolio", dest="portfolio", default="")
    parser.add_argument("--committee", action="store_true")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_workspace.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_workspace.production import (
        get_committee_workspace,
        get_company_workspace,
        get_portfolio_workspace,
    )

    if args.committee:
        result = get_committee_workspace()
    elif args.portfolio:
        result = get_portfolio_workspace(args.portfolio)
    else:
        result = get_company_workspace(args.company or "AXISBANK")

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Workspace unavailable", file=sys.stderr)
        return 1

    w = result["workspace"]
    print(w.get("title"))
    print()
    print("Timeline")
    print()
    for e in (w.get("timeline") or [])[:8]:
        print(f"- [{e.get('kind')}] {e.get('title')}")
    print()
    print("Linked objects")
    print()
    for o in w.get("linked_objects") or []:
        print(f"- {o.get('object_type')}: {o.get('label')} → {o.get('href')}")
    print()
    print(f"Evidence: {w.get('evidence_count')}  Notes: {w.get('note_count')}")
    print(f"Ask: {w.get('ask_deep_link')}")
    print(f"workspace_id: {w.get('workspace_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
