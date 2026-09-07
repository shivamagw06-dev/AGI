"""CLI — deterministic replay of Evaluation Lab results.

Examples:
  python -m institutional_evaluation_lab.replay --release PR306 --ticker HDFCBANK
  python -m institutional_evaluation_lab.replay --release PR306 --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay AGIB Evaluation Lab results (detect regressions)"
    )
    parser.add_argument("--release", required=True, help="Release id under results/")
    parser.add_argument("--ticker", default=None, help="Single ticker to replay")
    parser.add_argument("--limit", type=int, default=None, help="Replay first N tickers of a release")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args(argv)

    from institutional_evaluation_lab.replay.engine import replay_release, replay_ticker

    if args.ticker:
        out = replay_ticker(release_id=args.release, ticker=args.ticker)
    else:
        out = replay_release(release_id=args.release, limit=args.limit)

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if args.ticker:
            print(f"release:     {out.get('release_id')}")
            print(f"ticker:      {out.get('ticker')}")
            print(f"matched:     {out.get('ok')}")
            print(f"regression:  {out.get('regression')}")
            mismatches = (out.get("comparison") or {}).get("mismatches") or []
            if mismatches:
                print("mismatches:")
                for m in mismatches:
                    print(f"  - {m['field']}: stored={m['stored']!r} replayed={m['replayed']!r}")
        else:
            print(f"release:      {out.get('release_id')}")
            print(f"n:            {out.get('n')}")
            print(f"regressions:  {out.get('regressions')}")
            print(f"pass_pct:     {out.get('pass_pct')}")
            print(f"ok:           {out.get('ok')}")

    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
