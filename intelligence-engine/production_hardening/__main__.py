"""CLI: python -m production_hardening --suite|--regression|--scale smoke|--dashboard|--perf"""

from __future__ import annotations

import json
import sys

from production_hardening.production import (
    dashboard,
    data_quality,
    health,
    performance,
    regression,
    run_hardening_suite,
    scale,
    universe_info,
)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "Usage: python -m production_hardening "
            "--health|--suite|--regression|--regression-update|--dashboard|--dq|--perf|--scale PRESET|--universe PRESET"
        )
        sys.exit(1)
    cmd = args[0]
    if cmd == "--health":
        print(json.dumps(health(), indent=2, default=str))
        return
    if cmd == "--suite":
        preset = args[1] if len(args) > 1 else "smoke"
        print(json.dumps(run_hardening_suite(scale_preset=preset), indent=2, default=str))
        return
    if cmd == "--regression":
        print(json.dumps(regression(update_baseline=False), indent=2, default=str))
        return
    if cmd == "--regression-update":
        print(json.dumps(regression(update_baseline=True), indent=2, default=str))
        return
    if cmd == "--dashboard":
        print(json.dumps(dashboard(), indent=2, default=str))
        return
    if cmd == "--dq":
        print(json.dumps(data_quality(), indent=2, default=str))
        return
    if cmd == "--perf":
        print(json.dumps(performance(), indent=2, default=str))
        return
    if cmd == "--scale":
        preset = args[1] if len(args) > 1 else "smoke"
        limit = int(args[2]) if len(args) > 2 else None
        print(json.dumps(scale(preset=preset, limit=limit), indent=2, default=str))
        return
    if cmd == "--universe":
        preset = args[1] if len(args) > 1 else "smoke"
        print(json.dumps(universe_info(preset=preset), indent=2, default=str))
        return
    print("Unknown command", cmd)
    sys.exit(2)


if __name__ == "__main__":
    main()
