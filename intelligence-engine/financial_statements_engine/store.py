"""FSE store roots and path helpers."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parent / "data"


def store_root() -> Path:
    env = os.environ.get("FSE_STORE_ROOT", "").strip()
    return Path(env).expanduser() if env else _DEFAULT_ROOT


def ensure_dirs() -> Path:
    root = store_root()
    for name in (
        "raw",
        "raw_meta",
        "extracted",
        "normalized",
        "validated",
        "versions",
        "published",
        "derived",
        "indexes",
        "observability",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def paths_for(ticker: str) -> dict[str, Path]:
    root = ensure_dirs()
    t = ticker.upper().strip()
    return {
        "root": root,
        "raw": root / "raw" / t,
        "raw_meta": root / "raw_meta" / t,
        "extracted": root / "extracted" / t,
        "normalized": root / "normalized" / t,
        "validated": root / "validated" / t,
        "versions": root / "versions" / t,
        "published": root / "published" / t,
        "derived": root / "derived" / t,
    }
