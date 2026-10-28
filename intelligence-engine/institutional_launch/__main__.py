"""CLI: python -m institutional_launch"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="institutional_launch")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--sla", action="store_true")
    args = parser.parse_args(argv)

    from institutional_launch.production import health, metrics_api, report_api, sla_api

    if args.report:
        print(json.dumps(report_api(), indent=2, default=str))
        return 0
    if args.metrics:
        print(json.dumps(metrics_api(), indent=2, default=str))
        return 0
    if args.sla:
        print(json.dumps(sla_api(), indent=2, default=str))
        return 0
    print(json.dumps(health(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())