"""CLI: python -m company_memory TICKER | --ic10 | --health."""

from __future__ import annotations

import json
import sys

from company_memory.production import compile, health, ic10_compile


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "--health"}:
        print(json.dumps(health(), indent=2))
        return 0
    if args[0] == "--ic10":
        print(json.dumps(ic10_compile(persist=False), indent=2, default=str))
        return 0
    ticker = args[0].upper()
    use_cache = "--cache" in args
    mem = compile(ticker, persist="--no-persist" not in args, use_cache=use_cache)
    slim = {
        "display": mem.get("display"),
        "entity": mem.get("entity"),
        "ok": mem.get("ok"),
        "coverage": mem.get("coverage"),
        "confidence": mem.get("confidence"),
        "price": {
            "return_5y_pct": (mem.get("price_intelligence") or {}).get("return_5y_pct"),
            "return_10y_pct": (mem.get("price_intelligence") or {}).get("return_10y_pct"),
            "drawdown": (mem.get("price_intelligence") or {}).get("drawdown"),
        },
        "financial": {
            "revenue": (mem.get("financial_history") or {}).get("revenue"),
            "returns": (mem.get("financial_history") or {}).get("returns"),
        },
        "ownership_trends": (mem.get("ownership_history") or {}).get("trends"),
        "ownership_obs": (mem.get("ownership_history") or {}).get("observations"),
        "valuation": {
            "current": (mem.get("valuation_history") or {}).get("current"),
            "pe_band": ((mem.get("valuation_history") or {}).get("historical_bands") or {}).get("pe"),
            "stance": (mem.get("valuation_history") or {}).get("stance"),
        },
        "sector": (mem.get("sector_history") or {}).get("sector_key"),
        "corporate": (mem.get("corporate_history") or {}).get("observations"),
        "events_n": (mem.get("event_timeline") or {}).get("n"),
        "from_cache": mem.get("from_cache"),
        "latency_ms": mem.get("latency_ms"),
    }
    print(json.dumps(slim, indent=2, default=str))
    return 0 if mem.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
