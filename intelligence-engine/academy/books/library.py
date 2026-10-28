"""Personal library discovery — configured books directories only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


BOOK_EXTS = {".pdf", ".epub", ".docx", ".md", ".markdown", ".txt"}
SHEET_EXTS = {".xlsx", ".xls", ".ods"}
SUPPORTED_EXTS = BOOK_EXTS | SHEET_EXTS


def candidate_roots() -> list[Path]:
    """Ordered search roots for the personal investment library."""
    roots: list[Path] = []
    env = os.environ.get("ACADEMY_BOOKS_DIR") or os.environ.get("AGI_ACADEMY_BOOKS_DIR")
    if env:
        roots.append(Path(env).expanduser())
    try:
        from app.core.config import get_settings

        s = get_settings()
        cfg = getattr(s, "academy_books_dir", "") or ""
        if cfg:
            roots.append(Path(cfg).expanduser())
    except Exception:
        pass
    # AGIB project root Books/ (Finder often shows capital B)
    try:
        repo_root = Path(__file__).resolve().parents[3]
    except Exception:
        repo_root = Path("/workspace")
    # Prefer Books/ inside the Mac AGIB dump; fall back to the AGIB folder itself.
    roots.extend(preferred_mac_roots())
    roots.extend(
        [
            repo_root / "Books",
            repo_root / "books",
            Path("/workspace/Books"),
            Path("/workspace/books"),
        ]
    )
    # de-dupe preserve order
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def preferred_mac_roots() -> list[Path]:
    """Roots the user keeps on the Mac AGIB dump (may be absent in cloud agents)."""
    mac_agib = Path("/Users/shivamagarwal/Downloads/AGIB")
    home_agib = Path.home() / "Downloads" / "AGIB"
    return [
        mac_agib / "Books",
        mac_agib / "books",
        home_agib / "Books",
        home_agib / "books",
        mac_agib,
        home_agib,
    ]


def library_reachability() -> dict[str, Any]:
    """Report whether the Mac personal library is visible to this process."""
    preferred = preferred_mac_roots()
    existing_preferred = [str(p) for p in preferred if p.is_dir()]
    active = resolve_library_root()
    scan = scan_library(active) if active else {"ok": False, "counts": {}}
    cloud_fallback = Path("/workspace/books")
    return {
        "preferred_mac_path": "/Users/shivamagarwal/Downloads/AGIB/Books",
        "preferred_reachable": bool(existing_preferred),
        "preferred_existing": existing_preferred,
        "active_root": str(active) if active else None,
        "active_counts": (scan.get("counts") or {}),
        "cloud_fallback_root": str(cloud_fallback),
        "cloud_fallback_exists": cloud_fallback.is_dir(),
        "hint": (
            None
            if existing_preferred
            else (
                "Mac path is not mounted in this environment. Copy PDFs into the repo "
                "`books/` folder (gitignored) or run ingest on the Mac with "
                "ACADEMY_BOOKS_DIR=/Users/shivamagarwal/Downloads/AGIB/Books"
            )
        ),
    }


def resolve_library_root() -> Path | None:
    for r in candidate_roots():
        if r.is_dir():
            return r
    return None


def scan_library(root: Path | None = None) -> dict[str, Any]:
    root = root or resolve_library_root()
    if root is None or not root.is_dir():
        reach = {
            "preferred_mac_path": "/Users/shivamagarwal/Downloads/AGIB/Books",
            "preferred_reachable": any(p.is_dir() for p in preferred_mac_roots()),
            "hint": (
                "Mac Books folder not found. Sync PDFs into /workspace/books "
                "or set ACADEMY_BOOKS_DIR."
            ),
        }
        return {
            "ok": False,
            "root": None,
            "candidates": [str(p) for p in candidate_roots()],
            "files": [],
            "books": [],
            "spreadsheets": [],
            "unsupported": [],
            "reachability": reach,
        }
    books: list[dict[str, Any]] = []
    sheets: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        ext = path.suffix.lower()
        rel = str(path.relative_to(root))
        meta = {
            "path": str(path),
            "relative": rel,
            "filename": path.name,
            "ext": ext,
            "bytes": path.stat().st_size,
        }
        if ext in BOOK_EXTS:
            books.append(meta)
        elif ext in SHEET_EXTS:
            sheets.append(meta)
        elif ext in {".csv"}:
            # treat CSV as spreadsheet-like dataset
            sheets.append({**meta, "ext": ".csv", "as": "csv"})
        else:
            unsupported.append(meta)
    preferred_hit = any(
        str(root).startswith(str(p)) or root == p
        for p in preferred_mac_roots()
        if p.exists()
    )
    return {
        "ok": True,
        "root": str(root),
        "candidates": [str(p) for p in candidate_roots()],
        "files": books + sheets,
        "books": books,
        "spreadsheets": sheets,
        "unsupported": unsupported[:50],
        "counts": {
            "books": len(books),
            "spreadsheets": len(sheets),
            "unsupported": len(unsupported),
            "total_supported": len(books) + len(sheets),
        },
        "reachability": {
            "preferred_mac_path": "/Users/shivamagarwal/Downloads/AGIB/Books",
            "preferred_reachable": any(p.is_dir() for p in preferred_mac_roots()),
            "using_preferred_mac_library": preferred_hit,
            "hint": (
                None
                if preferred_hit
                else (
                    "Active root is a fallback (cloud/workspace). Mac Books at "
                    "/Users/shivamagarwal/Downloads/AGIB/Books is not visible here — "
                    "copy PDFs into repo books/ or ingest on the Mac."
                )
            ),
        },
    }
