"""CLI: python -m institutional_evaluation_lab.iat --release PR309 [--freeze]"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AGIB Phase 1 Institutional Acceptance Test")
    p.add_argument("--release", "--release-id", dest="release_id", required=True)
    p.add_argument("--previous", dest="previous_release", default=None)
    p.add_argument("--freeze", action="store_true", help="Freeze baseline only if IAT PASS")
    p.add_argument("--smoke", action="store_true", help="Advisory universe size (not official exam)")
    p.add_argument("--json", action="store_true", help="Print full JSON pack")
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args(argv)

    from institutional_evaluation_lab.iat.production import run_iat

    pack = run_iat(
        release_id=args.release_id,
        previous_release=args.previous_release,
        persist=not args.no_persist,
        freeze=args.freeze,
        require_full_universe=not args.smoke,
    )
    if args.json:
        print(json.dumps({k: v for k, v in pack.items() if k != "report_text"}, indent=2, default=str))
    else:
        print(pack.get("report_text") or json.dumps(pack, indent=2, default=str))
        freeze = pack.get("freeze") or {}
        if args.freeze:
            print()
            if freeze.get("frozen"):
                print(freeze.get("baseline", {}).get("freeze_prompt") or "FROZEN")
            else:
                print(f"Freeze refused: {freeze.get('reason')}")

    overall = (pack.get("overall") or {}).get("status")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
