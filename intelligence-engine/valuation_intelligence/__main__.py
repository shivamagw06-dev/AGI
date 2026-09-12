"""CLI: python -m valuation_intelligence TICKER [--max-peers N] [--ic10]."""

from __future__ import annotations

import json
import sys

from valuation_intelligence.production import analyse, health, ic10_smoke


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: python -m valuation_intelligence TICKER [--max-peers N]")
        print("       python -m valuation_intelligence --ic10")
        print(json.dumps(health(), indent=2))
        return 0
    if args[0] == "--ic10":
        print(json.dumps(ic10_smoke(max_peers=3, persist=False), indent=2, default=str))
        return 0
    ticker = args[0].upper()
    max_peers = 5
    if "--max-peers" in args:
        max_peers = int(args[args.index("--max-peers") + 1])
    pack = analyse(ticker, max_peers=max_peers, persist=False)
    slim = {
        "ticker": pack.get("ticker"),
        "ok": pack.get("ok"),
        "coverage_pct": pack.get("coverage_pct"),
        "current": pack.get("current"),
        "peers": (pack.get("peer_universe") or {}).get("primary_peers"),
        "peer_medians": ((pack.get("valuation") or {}).get("peers") or {}),
        "relative_pe": (pack.get("relative") or {}).get("pe"),
        "historical_pe": (pack.get("historical") or {}).get("pe"),
        "stance": pack.get("stance"),
        "observations": pack.get("observations"),
        "errors": pack.get("errors"),
        "latency_ms": pack.get("latency_ms"),
    }
    # Drop large peer snapshot lists from medians print
    if isinstance(slim["peer_medians"], dict):
        slim["peer_medians"] = {
            k: v for k, v in slim["peer_medians"].items() if k not in {"snapshots", "secondary", "universe"}
        }
    print(json.dumps(slim, indent=2, default=str))
    return 0 if pack.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
