"""CLI: python -m institutional_portfolio_risk --portfolio default"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_portfolio_risk",
        description=(
            "PRE-01 Institutional Portfolio Risk Engine — "
            "authoritative, versioned portfolio risk for the Investment Office"
        ),
    )
    parser.add_argument("--portfolio", "--portfolio-id", dest="portfolio", default="default")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_portfolio_risk.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    from institutional_portfolio_risk.production import evaluate_portfolio_risk

    result = evaluate_portfolio_risk({"portfolio_id": args.portfolio})
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Portfolio risk rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    r = result["risk"]
    print("Overall Risk")
    print()
    print(r.get("overall_risk"))
    print()
    print("Concentration")
    print()
    c = r.get("concentration") or {}
    print(
        f"{c.get('level')}  HHI={c.get('hhi')}  "
        f"largest={c.get('largest_position_ticker')}@{float(c.get('largest_position_weight') or 0):.0%}  "
        f"sector={c.get('top_sector')}@{float(c.get('sector_concentration') or 0):.0%}"
    )
    print()
    print("Stress")
    print()
    for s in r.get("stress_results") or []:
        print(
            f"- {s.get('label')}: {float(s.get('portfolio_impact_pct') or 0):+.1f}%  "
            f"[{s.get('severity')}]"
        )
    print()
    print("Warnings")
    print()
    warnings = r.get("warnings") or []
    if not warnings:
        print("(none)")
    for w in warnings:
        print(f"- {w}")
    print()
    print("Diagnostics")
    print()
    diag = result.get("diagnostics") or {}
    print(f"risk_id: {r.get('risk_id')}")
    print(f"risk_version: {r.get('risk_version')}")
    print(f"lineage: {' → '.join(r.get('lineage') or [])}")
    print(f"liquidity: {(r.get('liquidity') or {}).get('level')}")
    print(f"correlation: {(r.get('correlations') or {}).get('level')}")
    print(f"coverage: {(r.get('scorecard') or {}).get('coverage')}")
    print(f"latency_ms: {diag.get('latency_ms')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
