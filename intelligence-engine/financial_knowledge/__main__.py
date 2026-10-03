"""CLI: python -m financial_knowledge --metric ROCE"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(
            "usage: python -m financial_knowledge "
            "--health|--dashboard|--validate|"
            "--metric NAME|--ratio NAME|--relationship NAME|"
            "--glossary NAME|--threshold NAME|--sector NAME"
        )
        return 0

    cmd = args[0]
    if cmd == "--health":
        from financial_knowledge.production import health

        print(json.dumps(health(), indent=2, default=str))
        return 0
    if cmd == "--dashboard":
        from financial_knowledge.production import dashboard

        print(json.dumps(dashboard(), indent=2, default=str))
        return 0
    if cmd == "--validate":
        from financial_knowledge.registry import knowledge

        print(json.dumps(knowledge.validate(), indent=2, default=str))
        return 0

    from financial_knowledge.registry import knowledge

    lookups = {
        "--metric": knowledge.metric,
        "--ratio": knowledge.ratio,
        "--relationship": knowledge.relationship,
        "--glossary": knowledge.glossary,
        "--threshold": knowledge.threshold,
        "--sector": knowledge.sector,
    }
    if cmd in lookups:
        if len(args) < 2:
            print("name required", file=sys.stderr)
            return 2
        row = lookups[cmd](args[1])
        if row is None:
            print(json.dumps({"ok": False, "error": "not_found", "query": args[1]}, indent=2))
            return 1
        print(json.dumps({"ok": True, "result": row}, indent=2, default=str))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
