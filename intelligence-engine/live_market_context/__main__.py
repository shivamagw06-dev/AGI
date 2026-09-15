"""CLI: python -m live_market_context --ticker ETERNAL"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="P2.6 Live Market Context")
    p.add_argument("--ticker", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--intrinsic", type=float, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    from live_market_context.production import analyse

    pack = analyse(args.ticker, force=args.force, intrinsic_value=args.intrinsic)
    if args.json:
        print(json.dumps(pack, indent=2, default=str))
    else:
        panel = pack.get("panel") or {}
        print(f"{pack.get('engine_name')}  {pack.get('version')}")
        print(f"Ticker     {pack.get('ticker')}")
        print(f"LTP        {panel.get('ltp')} {panel.get('currency')}")
        print(f"Provider   {panel.get('provider')}")
        print(f"Fresh      {(panel.get('price_freshness') or {}).get('within_sla')}")
        print(f"Liquidity  {(panel.get('liquidity') or {}).get('band')}")
        print(f"RS         {(panel.get('relative_strength') or {}).get('band')}")
        print(f"Confidence {pack.get('confidence')}")
        print(f"Degraded   {pack.get('degraded')}")
    return 0 if pack.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
