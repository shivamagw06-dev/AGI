"""Failure database — catalogue why AIG failed, not only that it failed."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parent / "state" / "red_team_failures.jsonl"


def build_failure_record(
    *,
    question: str,
    expected_category: str | None,
    detected_family: str | None,
    detected_mode: str | None,
    evidence_used: list[str] | None = None,
    evidence_missed: list[str] | None = None,
    reasoning_mistake: str | None = None,
    editorial_mistake: str | None = None,
    root_cause: str | None = None,
    fix: str | None = None,
    ecr: dict[str, Any] | None = None,
    answer_preview: str | None = None,
    test_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured failure record matching the lab template."""
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "test_id": test_id,
        "question": question,
        "expected_reasoning_family_or_category": expected_category,
        "detected_family": detected_family,
        "detected_mode": detected_mode,
        "evidence_used": list(evidence_used or []),
        "evidence_missed": list(evidence_missed or []),
        "reasoning_mistake": reasoning_mistake,
        "editorial_mistake": editorial_mistake,
        "root_cause": root_cause,
        "fix": fix,
        "ecr": ecr or {},
        "answer_preview": (answer_preview or "")[:400],
        "extra": extra or {},
    }


def append_failure(record: dict[str, Any], path: Path | None = None) -> Path:
    target = path or DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target


def load_failures(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or DEFAULT_PATH
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def summarise_failures(path: Path | None = None) -> dict[str, Any]:
    rows = load_failures(path)
    by_category: dict[str, int] = {}
    by_root: dict[str, int] = {}
    for row in rows:
        cat = str(row.get("expected_reasoning_family_or_category") or "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1
        root = str(row.get("root_cause") or "unspecified")
        by_root[root] = by_root.get(root, 0) + 1
    return {
        "total_failures_logged": len(rows),
        "by_category": by_category,
        "by_root_cause": by_root,
        "path": str(path or DEFAULT_PATH),
    }
