"""CLI for Academy Books library scan / ingest.

Run on the Mac (where Downloads/AGIB/Books is visible) or after syncing
PDFs into the repo `books/` folder for cloud agents.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGI Academy Books — learn from personal PDFs")
    parser.add_argument(
        "command",
        choices=("status", "scan", "ingest"),
        help="status=reachability, scan=list files, ingest=structured learn + persist",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Library root (default: auto). Example: /Users/shivamagarwal/Downloads/AGIB/Books",
    )
    parser.add_argument("--limit", type=int, default=None, help="Ingest at most N files")
    args = parser.parse_args(argv)

    from academy.books.library import library_reachability, scan_library
    from academy.books.batch import ingest_personal_library

    root = Path(args.root).expanduser() if args.root else None

    if args.command == "status":
        payload = library_reachability()
        if root is not None:
            payload["override_root"] = str(root)
            payload["override_exists"] = root.is_dir()
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("preferred_reachable") or payload.get("active_root") else 2

    if args.command == "scan":
        payload = scan_library(root)
        # Compact listing for humans
        slim = {
            "ok": payload.get("ok"),
            "root": payload.get("root"),
            "counts": payload.get("counts"),
            "reachability": payload.get("reachability"),
            "books": [b.get("filename") for b in (payload.get("books") or [])],
        }
        print(json.dumps(slim, indent=2))
        return 0 if payload.get("ok") else 2

    # ingest
    report = ingest_personal_library(root=root, limit=args.limit)
    slim = {
        "ok": report.get("ok"),
        "library_root": report.get("library_root"),
        "attempted": report.get("attempted"),
        "succeeded": report.get("succeeded"),
        "failed": report.get("failed"),
        "persisted": report.get("persisted"),
        "store": report.get("store"),
        "reachability_hint": (report.get("reports") and None),
        "files": [
            {
                "filename": r.get("filename"),
                "ok": r.get("ok"),
                "concepts": r.get("concepts_extracted"),
                "formulas": r.get("formulas_extracted"),
                "quality": r.get("extraction_quality"),
            }
            for r in (report.get("reports") or [])
        ],
    }
    # Attach reachability for cloud vs Mac clarity
    slim["reachability"] = library_reachability()
    print(json.dumps(slim, indent=2))
    return 0 if report.get("ok") and int(report.get("failed") or 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
