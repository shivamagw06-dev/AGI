"""CLI: python -m institutional_publishing --type MorningBrief"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_publishing",
        description="PUB-01 Publishing & Distribution — compose institutional deliverables",
    )
    parser.add_argument("--type", dest="ptype", default="MorningBrief")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--portfolio", default="agi-core-equity")
    parser.add_argument("--renderer", default="markdown")
    parser.add_argument("--query", default="")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--types", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.health:
        from institutional_publishing.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0

    if args.types:
        from institutional_publishing.production import list_types

        print(json.dumps(list_types(), indent=2, default=str))
        return 0

    from institutional_publishing.production import generate

    result = generate(
        {
            "publication_type": args.ptype,
            "ticker": args.ticker,
            "portfolio_id": args.portfolio,
            "renderer": args.renderer,
            "query": args.query,
        }
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print("Publication rejected:", result.get("validation_errors"), file=sys.stderr)
        return 1

    pub = result["publication"]
    print(pub.get("title"))
    print()
    print(f"id: {pub.get('publication_id')}")
    print(f"type: {pub.get('publication_type')}")
    print(f"compose_only: {result.get('compose_only')}")
    print(f"lineage_hash: {(pub.get('manifest') or {}).get('lineage_hash')}")
    print()
    print((result.get("render") or {}).get("artifact") or pub.get("body_markdown") or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
