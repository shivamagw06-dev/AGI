"""Capability gate — new capabilities must fail a new adversarial test first.

This keeps development grounded in real weaknesses instead of feature sprawl.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from red_team.rules import CAPABILITY_GATE_RULE

REGISTRY_PATH = Path(__file__).resolve().parent / "state" / "capability_gate_registry.json"


def _empty_registry() -> dict[str, Any]:
    return {
        "rule": CAPABILITY_GATE_RULE,
        "capabilities": {},
        "updated_at": None,
    }


def load_registry(path: Path | None = None) -> dict[str, Any]:
    target = path or REGISTRY_PATH
    if not target.exists():
        return _empty_registry()
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty_registry()


def save_registry(registry: dict[str, Any], path: Path | None = None) -> Path:
    target = path or REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    registry["rule"] = CAPABILITY_GATE_RULE
    target.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def register_failing_test(
    *,
    capability_id: str,
    test_id: str,
    question: str,
    notes: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    """Record that a capability was first shown to fail on a new adversarial test."""
    reg = load_registry(path)
    caps = reg.setdefault("capabilities", {})
    row = caps.get(capability_id) or {
        "capability_id": capability_id,
        "status": "blocked_pending_failing_test",
        "failing_tests": [],
        "production_allowed": False,
    }
    entry = {
        "test_id": test_id,
        "question": question,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "initial_result": "fail",
    }
    existing_ids = {t.get("test_id") for t in row.get("failing_tests") or []}
    if test_id not in existing_ids:
        row.setdefault("failing_tests", []).append(entry)
    row["status"] = "has_failing_test"
    caps[capability_id] = row
    save_registry(reg, path)
    return row


def mark_production_allowed(
    *,
    capability_id: str,
    reason: str,
    path: Path | None = None,
) -> dict[str, Any]:
    """Allow production only after a failing adversarial test is on file."""
    reg = load_registry(path)
    caps = reg.setdefault("capabilities", {})
    row = caps.get(capability_id)
    if not row or not row.get("failing_tests"):
        raise ValueError(
            f"Capability {capability_id!r} cannot enter production: "
            "no failing adversarial test registered."
        )
    row["production_allowed"] = True
    row["status"] = "production_allowed"
    row["allowed_reason"] = reason
    row["allowed_at"] = datetime.now(timezone.utc).isoformat()
    caps[capability_id] = row
    save_registry(reg, path)
    return row


def gate_check(capability_id: str, path: Path | None = None) -> dict[str, Any]:
    reg = load_registry(path)
    row = (reg.get("capabilities") or {}).get(capability_id)
    if not row:
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "unregistered_capability",
            "rule": CAPABILITY_GATE_RULE,
        }
    allowed = bool(row.get("production_allowed") and row.get("failing_tests"))
    return {
        "capability_id": capability_id,
        "allowed": allowed,
        "status": row.get("status"),
        "failing_test_count": len(row.get("failing_tests") or []),
        "rule": CAPABILITY_GATE_RULE,
        "record": row,
    }
