"""Persist gold regression fingerprints and hardening run history."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from production_hardening.util import now_iso


def _root() -> Path:
    override = os.environ.get("AGIB_HARDENING_RESULTS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "results"


def gold_path() -> Path:
    return _root() / "gold_fingerprints.json"


def history_path() -> Path:
    return _root() / "run_history.jsonl"


def load_gold() -> dict[str, Any]:
    path = gold_path()
    if not path.exists():
        return {"version": 1, "companies": {}, "updated_at": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "companies": {}, "updated_at": None, "error": "corrupt_gold_file"}


def save_gold(payload: dict[str, Any]) -> dict[str, Any]:
    root = _root()
    root.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "updated_at": now_iso()}
    gold_path().write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    # Also write latest.md summary
    lines = ["# Gold Regression Fingerprints", "", f"Updated: {payload.get('updated_at')}", ""]
    for t, row in sorted((payload.get("companies") or {}).items()):
        lines.append(f"- **{t}**: `{row.get('fingerprint')}` score={row.get('opportunity_score')} priority={row.get('research_priority')}")
    (root / "gold_fingerprints.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"written": True, "path": str(gold_path())}


def append_history(row: dict[str, Any]) -> None:
    root = _root()
    root.mkdir(parents=True, exist_ok=True)
    with history_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps({**row, "at": now_iso()}, default=str) + "\n")


def latest_history(limit: int = 20) -> list[dict[str, Any]]:
    path = history_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows[-max(1, min(int(limit), 200)) :]
