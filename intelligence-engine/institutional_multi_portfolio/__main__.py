"""CLI: python -m institutional_multi_portfolio --portfolio growth-portfolio"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_multi_portfolio",
        description="MPC-01 Multi-Portfolio & Client Platform — tenancy/workflow over shared intelligence",
    )
    parser.add_argument("--portfolio", default="agi-core-equity")
    parser.add_argument("--client", default="")
    parser.add_argument("--role", default="analyst")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_multi_portfolio.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    if args.list:
        from institutional_multi_portfolio.production import list_clients_api, list_portfolios_api

        print(json.dumps({"portfolios": list_portfolios_api(), "clients": list_clients_api()}, indent=2, default=str))
        return 0

    from institutional_multi_portfolio.production import get_workspace

    result = get_workspace(
        portfolio_id=args.portfolio,
        client_id=args.client,
        role_id=args.role,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Workspace resolve failed", result.get("validation_errors"), file=sys.stderr)
        return 1

    ws = result["workspace"]
    print(ws.get("workspace_id"))
    print(f"portfolio: {ws.get('portfolio_id')}")
    print(f"mandate: {ws.get('mandate')} → policy {ws.get('policy_profile')}")
    print(f"role: {ws.get('role_id')}")
    print(f"permissions: {', '.join(ws.get('permissions') or [])}")
    print(f"ask: {ws.get('ask_deep_link')}")
    print(f"research: {ws.get('research_deep_link')}")
    print("intelligence_is_global: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
