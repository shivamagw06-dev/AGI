"""CLI: python -m investment_operations --morning | --queue | --ic10 | TICKER"""

from __future__ import annotations

import json
import sys

from investment_operations.production import (
    decision_replay,
    health,
    ic10_smoke,
    morning_office,
    research_queue,
    workspace,
)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m investment_operations --morning|--queue|--ic10|--health|TICKER")
        sys.exit(1)
    cmd = args[0]
    if cmd == "--health":
        print(json.dumps(health(), indent=2, default=str))
        return
    if cmd == "--morning":
        print(json.dumps(morning_office(include_soft_reasoning=False), indent=2, default=str))
        return
    if cmd == "--queue":
        print(json.dumps(research_queue(include_soft_reasoning=False), indent=2, default=str))
        return
    if cmd == "--ic10":
        print(json.dumps(ic10_smoke(), indent=2, default=str))
        return
    if cmd == "--replay":
        t = args[1] if len(args) > 1 else "TCS"
        print(json.dumps(decision_replay(t), indent=2, default=str))
        return
    print(json.dumps(workspace(cmd, include_soft_reasoning=False), indent=2, default=str))


if __name__ == "__main__":
    main()
