"""CLI: python -m institutional_decision --ticker AXISBANK"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_decision",
        description="IDS-01 Institutional Decision System (deterministic, no LLM)",
    )
    parser.add_argument("--ticker", required=False)
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-history", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_decision.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    ticker = (args.ticker or "").strip()
    if not ticker:
        parser.error("--ticker is required unless --health")

    from institutional_decision.production import decide_company

    result = decide_company({"ticker": ticker, "include_history": args.include_history})
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Decision rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    d = result["decision"]
    diag = result.get("diagnostics") or {}
    print("Institutional Decision")
    print()
    print("Recommendation")
    print()
    print(d.get("recommendation"))
    print()
    print("Conviction")
    print()
    print(d.get("conviction"))
    print()
    print("Confidence")
    print()
    print(d.get("confidence"))
    print()
    print("Reasons")
    print()
    for r in d.get("supporting_reasons") or []:
        print(f"- {r}")
    print()
    print("Contradicting Reasons")
    print()
    for r in d.get("contradicting_reasons") or []:
        print(f"- {r}")
    print()
    print("Upgrade Conditions")
    print()
    for r in d.get("upgrade_conditions") or []:
        print(f"- {r}")
    print()
    print("Downgrade Conditions")
    print()
    for r in d.get("downgrade_conditions") or []:
        print(f"- {r}")
    print()
    print("Monitoring")
    print()
    for r in d.get("monitoring_items") or []:
        print(f"- {r}")
    print()
    print("Diagnostics")
    print()
    for key in (
        "decision_id",
        "decision_version",
        "evidence_count",
        "validator_result",
        "score",
        "rule_path",
        "evidence_snapshot_id",
    ):
        print(f"{key}: {diag.get(key)}")
    if args.include_history:
        print()
        print("History")
        print()
        print(json.dumps(result.get("history") or [], indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
