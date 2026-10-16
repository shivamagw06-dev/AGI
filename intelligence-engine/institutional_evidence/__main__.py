"""CLI: python -m institutional_evidence [ticker]"""

from __future__ import annotations

import json
import sys

from .production import get_iep_status, get_phase1_coverage, get_research_pack, orchestrate_research


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"status", "health"}:
        print(json.dumps(get_iep_status(), indent=2, default=str))
        return 0
    if args[0] == "phase1":
        print(json.dumps(get_phase1_coverage(), indent=2, default=str))
        return 0
    if args[0] == "orchestrate" and len(args) > 1:
        print(json.dumps(orchestrate_research(args[1]), indent=2, default=str))
        return 0
    ticker = args[0].upper()
    print(json.dumps(get_research_pack(ticker), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
