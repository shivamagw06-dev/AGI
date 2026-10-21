"""CLI: python -m institutional_calibration --ticker AXISBANK"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_calibration",
        description="IDS-02 Decision Calibration & Explainability (deterministic, no LLM)",
    )
    parser.add_argument("--ticker", required=False)
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-drift", action="store_true", default=True)
    parser.add_argument("--no-drift", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_calibration.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    ticker = (args.ticker or "").strip()
    if not ticker:
        parser.error("--ticker is required unless --health")

    from institutional_decision.production import decide_company

    include_drift = not args.no_drift
    result = decide_company(
        {
            "ticker": ticker,
            "include_calibration": True,
            "include_drift": include_drift,
        }
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Calibration / decision rejected", file=sys.stderr)
        print(json.dumps(result.get("validation_errors") or [], indent=2), file=sys.stderr)
        return 1

    d = result.get("decision") or {}
    cal = result.get("calibration") or {}
    scorecard = result.get("scorecard") or {}
    drift = result.get("drift") or {}

    print("Recommendation")
    print()
    print(d.get("recommendation"))
    print()
    print("Confidence")
    print()
    print(d.get("confidence"))
    print()
    print("Calibration")
    print()
    components = cal.get("components") or {}
    for key in (
        "evidence_quality",
        "evidence_freshness",
        "evidence_coverage",
        "reasoning_strength",
        "rule_consistency",
        "valuation_certainty",
        "forecast_stability",
        "macro_stability",
        "unknown_penalty",
        "contradiction_penalty",
    ):
        if key in components:
            print(f"{key}: {components[key]}")
    print(f"profile_version: {cal.get('profile_version')}")
    print()
    print("Decision Scorecard")
    print()
    for line in scorecard.get("lines") or []:
        pts = line.get("points")
        sign = f"+{pts}" if isinstance(pts, int) and pts > 0 else str(pts)
        print(f"{line.get('dimension')}: {sign}")
    print()
    print(f"Final Decision: {scorecard.get('recommendation')}")
    print(f"Confidence: {scorecard.get('confidence')}%")
    print()
    print("Confidence Breakdown")
    print()
    print("Positive")
    for c in cal.get("positive") or []:
        print(f"+ {c.get('label')}")
    print()
    print("Negative")
    for c in cal.get("negative") or []:
        print(f"- {c.get('label')}")
    print()
    print("Decision Drift")
    print()
    if drift.get("has_previous"):
        print(f"{drift.get('previous_recommendation')} → {drift.get('current_recommendation')}")
        for step in drift.get("explanation_chain") or []:
            print(f"- {step}")
    else:
        print("No previous decision")
        for step in drift.get("explanation_chain") or []:
            print(f"- {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
