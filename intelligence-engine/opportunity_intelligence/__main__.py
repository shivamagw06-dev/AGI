"""CLI: python -m opportunity_intelligence TICKER | --ic10 | --top | --watchlist"""

from __future__ import annotations

import json
import sys

from opportunity_intelligence.production import analyse, catalysts, health, ic10_smoke, top, watchlist


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m opportunity_intelligence TICKER")
        print("       python -m opportunity_intelligence --ic10")
        print("       python -m opportunity_intelligence --top")
        print("       python -m opportunity_intelligence --watchlist")
        print("       python -m opportunity_intelligence --health")
        sys.exit(1)
    cmd = args[0]
    if cmd == "--health":
        print(json.dumps(health(), indent=2, default=str))
        return
    if cmd == "--ic10":
        print(json.dumps(ic10_smoke(), indent=2, default=str))
        return
    if cmd == "--top":
        print(json.dumps(top(limit=10), indent=2, default=str))
        return
    if cmd == "--watchlist":
        print(json.dumps(watchlist(), indent=2, default=str))
        return
    if cmd == "--catalysts":
        print(json.dumps(catalysts(), indent=2, default=str))
        return
    print(json.dumps(analyse(cmd, persist_memory=False), indent=2, default=str))


if __name__ == "__main__":
    main()
