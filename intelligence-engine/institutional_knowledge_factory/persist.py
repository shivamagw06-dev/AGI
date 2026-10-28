"""Persistent Knowledge Object store — compiled IKOs survive restarts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def store_root() -> Path:
    raw = (os.getenv("IKO_STORE_ROOT") or "").strip()
    if raw:
        root = Path(raw)
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "iko"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(entity_id: str) -> Path:
    return store_root() / f"{entity_id.upper()}.json"


def save_iko(iko: dict[str, Any]) -> dict[str, Any]:
    entity_id = str(iko.get("entity_id") or "").upper()
    if not entity_id:
        raise ValueError("iko.entity_id required")
    path = _path(entity_id)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(iko, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    return iko


def load_iko(entity_id: str) -> dict[str, Any] | None:
    path = _path(entity_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_compiled() -> list[str]:
    return sorted(p.stem for p in store_root().glob("*.json"))
