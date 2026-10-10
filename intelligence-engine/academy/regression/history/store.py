"""Immutable release history — append-only intelligence evolution log."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from academy.regression.schema import IRS_VERSION

_LOCK = Lock()
_MEMORY: list[dict[str, Any]] = []
_PATH = Path(__file__).resolve().parent / "data" / "release_history.jsonl"


def _ensure() -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _MEMORY and _PATH.exists():
        for line in _PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    _MEMORY.append(json.loads(line))
                except Exception:
                    continue


def seed_baseline_if_empty(baseline: dict[str, Any]) -> None:
    """Seed a baseline previous release so first PR can compute deltas."""
    with _LOCK:
        _ensure()
        if _MEMORY:
            return
        row = {
            "release": "baseline",
            "irs_version": IRS_VERSION,
            "overall_institutional_iq": baseline.get("overall_institutional_iq"),
            "reasoning_scores": baseline.get("reasoning_scores") or {},
            "hallucinations": {
                "critical": (baseline.get("hallucinations") or {}).get("critical_count", 0),
                "high": (baseline.get("hallucinations") or {}).get("high_count", 0),
            },
            "analyst_drift_total": (baseline.get("analyst_drift") or {}).get("total", 0),
            "snapshot": {
                "overall_institutional_iq": baseline.get("overall_institutional_iq"),
                "reasoning_scores": baseline.get("reasoning_scores"),
                "evidence_score_mean": baseline.get("evidence_score_mean"),
                "framework_score_mean": baseline.get("framework_score_mean"),
            },
        }
        _MEMORY.append(row)
        with _PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


def append_release(record: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        _ensure()
        row = deepcopy(record)
        _MEMORY.append(row)
        with _PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return deepcopy(row)


def latest() -> dict[str, Any] | None:
    with _LOCK:
        _ensure()
        return deepcopy(_MEMORY[-1]) if _MEMORY else None


def previous() -> dict[str, Any] | None:
    with _LOCK:
        _ensure()
        if len(_MEMORY) < 1:
            return None
        # latest is current in-flight; previous for delta is last stored
        return deepcopy(_MEMORY[-1])


def all_releases() -> list[dict[str, Any]]:
    with _LOCK:
        _ensure()
        return deepcopy(_MEMORY)


def reset_for_tests() -> None:
    with _LOCK:
        _MEMORY.clear()
        if _PATH.exists():
            _PATH.unlink()
