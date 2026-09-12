"""CLI — run the Phase 1 golden universe Evaluation Lab.

Examples:
  python -m institutional_evaluation_lab.golden_universe --release-id PR306 --limit 10
  python -m institutional_evaluation_lab.golden_universe --release-id PR306 --persist-baseline
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AGIB Institutional Evaluation Lab — golden universe runner (PR #306)"
    )
    parser.add_argument("--release-id", default="PR306", help="Results folder name under results/")
    parser.add_argument("--limit", type=int, default=None, help="Optional ticker limit (default: all 200)")
    parser.add_argument("--bucket", default=None, help="Optional bucket filter")
    parser.add_argument("--force-price-refresh", action="store_true")
    parser.add_argument("--persist-baseline", action="store_true", help="Also write phase1_golden_baseline.json")
    parser.add_argument("--no-persist", action="store_true", help="Skip writing results/ tree")
    parser.add_argument("--no-compare", action="store_true", help="Skip drift vs previous baseline")
    parser.add_argument("--json", action="store_true", help="Print full summary JSON to stdout")
    args = parser.parse_args(argv)

    from institutional_evaluation_lab.golden_universe.runner import run_golden_evaluation

    summary = run_golden_evaluation(
        limit=args.limit,
        bucket=args.bucket,
        force_price_refresh=args.force_price_refresh,
        persist=not args.no_persist,
        persist_baseline=args.persist_baseline,
        compare_previous=not args.no_compare,
        release_id=args.release_id,
    )

    if args.json:
        light = {k: v for k, v in summary.items() if k not in {"rows", "drift_table"}}
        light["rows_sample"] = (summary.get("rows") or [])[:5]
        print(json.dumps(light, indent=2, default=str))
    else:
        results = summary.get("results") or {}
        cov = summary.get("coverage") or {}
        print(f"release_id:     {summary.get('release_id')}")
        print(f"n:              {summary.get('n')}")
        print(f"results_dir:    {results.get('results_dir') or summary.get('results_dir')}")
        print(f"avg_readiness:  {cov.get('average_readiness_pct')}")
        print(f"gate_pass_pct:  {cov.get('gate_pass_rate_pct')}")
        print(f"avg_runtime_s:  {cov.get('average_runtime_s')}")
        print(f"ticker_files:   {results.get('n')}")
        print("layout:         results/{release_id}/{TICKER}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
