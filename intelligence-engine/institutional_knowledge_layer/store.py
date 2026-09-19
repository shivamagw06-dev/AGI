"""Durable IKL store (JSONL under AGIB_DATA_DIR). Soft — never raises."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()


def _root() -> Path:
    base = (os.environ.get("AGIB_DATA_DIR") or "").strip()
    root = Path(base) if base else Path(__file__).resolve().parents[1] / "data"
    path = root / "ikl"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_key(key: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in (key or "").strip())[:120] or "unknown"


def memory_path(kind: str, key: str) -> Path:
    return _root() / "memory" / kind / f"{_safe_key(key)}.json"


def load_memory(kind: str, key: str) -> dict[str, Any] | None:
    try:
        path = memory_path(kind, key)
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def save_memory(kind: str, key: str, payload: dict[str, Any]) -> bool:
    try:
        path = memory_path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = dict(payload or {})
        body["updated_at"] = float(body.get("updated_at") or time.time())
        tmp = path.with_suffix(".tmp")
        with _LOCK:
            tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            tmp.replace(path)
        return True
    except Exception:
        return False


def append_jsonl(name: str, row: dict[str, Any]) -> bool:
    try:
        path = _root() / f"{_safe_key(name)}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(row, ensure_ascii=False, default=str)
        with _LOCK:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return True
    except Exception:
        return False


def load_jsonl_tail(name: str, *, limit: int = 200) -> list[dict[str, Any]]:
    try:
        path = _root() / f"{_safe_key(name)}.jsonl"
        if not path.is_file():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-max(1, int(limit)) :]:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                out.append(row)
        return out
    except Exception:
        return []


def list_memory_keys(kind: str, *, limit: int = 200) -> list[str]:
    try:
        folder = _root() / "memory" / kind
        if not folder.is_dir():
            return []
        keys = sorted(p.stem for p in folder.glob("*.json"))
        return keys[: max(1, int(limit))]
    except Exception:
        return []
