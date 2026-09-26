"""CLI: python -m autonomous_research --status | --planner | --ic10 | TICKER"""

from __future__ import annotations

import json
import sys

from autonomous_research.production import health, ic10_smoke, planner, research, status


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m autonomous_research --status|--planner|--ic10|--health|TICKER")
        sys.exit(1)
    cmd = args[0]
    if cmd == "--health":
        print(json.dumps(health(), indent=2, default=str))
        return
    if cmd == "--status":
        print(json.dumps(status(holdings=["TCS", "HAL"]), indent=2, default=str))
        return
    if cmd == "--planner":
        print(json.dumps(planner(holdings=["TCS", "HAL"]), indent=2, default=str))
        return
    if cmd == "--ic10":
        print(json.dumps(ic10_smoke(), indent=2, default=str))
        return
    print(json.dumps(research(cmd), indent=2, default=str))


if __name__ == "__main__":
    main()
