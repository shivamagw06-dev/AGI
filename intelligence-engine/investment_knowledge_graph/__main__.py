"""CLI: python -m investment_knowledge_graph TICKER | --theme AI | --macro."""

from __future__ import annotations

import json
import sys

from investment_knowledge_graph.production import analyse, health, macro, retrieve, theme


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "--health"}:
        print(json.dumps(health(), indent=2))
        return 0
    if args[0] == "--theme":
        print(json.dumps(theme(args[1] if len(args) > 1 else "AI"), indent=2, default=str))
        return 0
    if args[0] == "--macro":
        print(json.dumps(macro(args[1] if len(args) > 1 else None), indent=2, default=str))
        return 0
    if args[0] == "--retrieve":
        ticker = args[1].upper() if len(args) > 1 else "TCS"
        pack = retrieve(ticker, include_cid=False, persist_delta=False)
        slim = {
            "entity": pack.get("entity"),
            "memory_version": (pack.get("company_memory") or {}).get("version"),
            "delta": (pack.get("latest_delta") or {}).get("summary"),
            "peers": (pack.get("knowledge_graph") or {}).get("peers"),
            "themes": (pack.get("knowledge_graph") or {}).get("themes"),
            "sector_chain": (pack.get("knowledge_graph") or {}).get("sector_chain"),
            "n_nodes": (pack.get("knowledge_graph") or {}).get("n_nodes"),
            "n_edges": (pack.get("knowledge_graph") or {}).get("n_edges"),
        }
        print(json.dumps(slim, indent=2, default=str))
        return 0
    pack = analyse(args[0].upper())
    g = pack.get("knowledge_graph") or pack
    slim = {
        "entity": g.get("entity"),
        "sector_key": g.get("sector_key"),
        "peers": g.get("peers"),
        "themes": g.get("themes"),
        "sector_chain": g.get("sector_chain"),
        "n_nodes": g.get("n_nodes"),
        "n_edges": g.get("n_edges"),
        "sample_edges": (g.get("edges") or [])[:12],
    }
    print(json.dumps(slim, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
