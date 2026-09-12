"""CLI: python -m institutional_observability"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="institutional_observability")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--service-map", action="store_true")
    parser.add_argument("--alerts", action="store_true")
    args = parser.parse_args(argv)

    from institutional_observability.production import (
        health,
        ops_alerts,
        ops_metrics,
        ops_service_map,
    )

    if args.metrics:
        print(json.dumps(ops_metrics(), indent=2, default=str))
        return 0
    if args.service_map:
        print(json.dumps(ops_service_map(), indent=2, default=str))
        return 0
    if args.alerts:
        print(json.dumps(ops_alerts(), indent=2, default=str))
        return 0
    print(json.dumps(health(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())