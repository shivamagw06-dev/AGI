"""CLI: python -m knowledge_delta_engine TICKER [--explain TOPIC] [--versions]."""

from __future__ import annotations

import json
import sys

from knowledge_delta_engine.production import compile_incremental, explain, health, ledger, versions


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "--health"}:
        print(json.dumps(health(), indent=2))
        return 0
    ticker = args[0].upper()
    if "--versions" in args:
        print(json.dumps(versions(ticker), indent=2, default=str))
        return 0
    if "--ledger" in args:
        print(json.dumps(ledger(ticker), indent=2, default=str))
        return 0
    if "--explain" in args:
        topic = args[args.index("--explain") + 1] if args.index("--explain") + 1 < len(args) else "management_confidence"
        print(json.dumps(explain(ticker, topic=topic), indent=2, default=str))
        return 0
    pack = compile_incremental(ticker, persist="--no-persist" not in args)
    slim = {
        "entity": pack.get("entity"),
        "ok": pack.get("ok"),
        "noop": pack.get("noop"),
        "incremental": pack.get("incremental"),
        "memory_version": pack.get("memory_version"),
        "memory_delta": {
            "status": (pack.get("memory_delta") or {}).get("status"),
            "summary": (pack.get("memory_delta") or {}).get("summary"),
            "n_field_changes": (pack.get("memory_delta") or {}).get("n_field_changes"),
            "observations": (pack.get("memory_delta") or {}).get("observations"),
        },
        "delta_engine": pack.get("delta_engine"),
        "coverage": pack.get("coverage"),
        "latency_ms": pack.get("latency_ms"),
    }
    print(json.dumps(slim, indent=2, default=str))
    return 0 if pack.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
