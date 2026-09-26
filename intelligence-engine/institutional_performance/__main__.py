"""CLI: python -m institutional_performance"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="institutional_performance")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--cache-stats", action="store_true")
    parser.add_argument("--queue", action="store_true")
    parser.add_argument("--parallel-demo", action="store_true")
    args = parser.parse_args(argv)

    from institutional_performance.production import (
        cache_stats,
        health,
        metrics_api,
        parallel_demo,
        queue_stats_api,
    )

    if args.metrics:
        print(json.dumps(metrics_api(), indent=2, default=str))
        return 0
    if args.cache_stats:
        print(json.dumps(cache_stats(), indent=2, default=str))
        return 0
    if args.queue:
        print(json.dumps(queue_stats_api(), indent=2, default=str))
        return 0
    if args.parallel_demo:
        print(json.dumps(parallel_demo({"sleep": 0.02}), indent=2, default=str))
        return 0
    print(json.dumps(health(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
