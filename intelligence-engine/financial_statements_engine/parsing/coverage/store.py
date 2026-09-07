"""Immutable persistence for Evidence Coverage Matrices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import write_json_atomic


def _matrix_dir(ticker: str) -> Path:
    p = ensure_dirs() / "parsing" / "coverage" / "matrices" / ticker.upper().strip()
    p.mkdir(parents=True, exist_ok=True)
    return p


def store_matrix(matrix: dict[str, Any]) -> Path:
    ticker = str(matrix["ticker"]).upper().strip()
    mid = str(matrix["matrix_id"])
    path = _matrix_dir(ticker) / f"{mid.replace(':', '_')}.json"
    if path.exists():
        raise FileExistsError(f"coverage_matrix_immutable_violation: {mid}")
    write_json_atomic(path, matrix)
    # latest pointer (mutable pointer only)
    write_json_atomic(
        _matrix_dir(ticker) / "latest.json",
        {
            "matrix_id": mid,
            "manifest_id": matrix.get("manifest_id"),
            "document_hash": matrix.get("document_hash"),
            "path": str(path),
            "coverage_fingerprint": matrix.get("coverage_fingerprint"),
        },
    )
    return path


def load_matrix(ticker: str, matrix_id: str) -> dict[str, Any] | None:
    path = _matrix_dir(ticker) / f"{matrix_id.replace(':', '_')}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_matrices(ticker: str) -> list[dict[str, Any]]:
    root = _matrix_dir(ticker)
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("ecm_*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows


def store_bundle(
    *,
    matrix: dict[str, Any],
    scorecard: dict[str, Any],
    missing_report: dict[str, Any],
    unknown_report: dict[str, Any],
) -> Path:
    """Store matrix + sidecar reports under one immutable matrix id."""
    path = store_matrix(matrix)
    side = path.with_suffix(".bundle.json")
    if side.exists():
        raise FileExistsError(f"coverage_bundle_immutable_violation: {matrix['matrix_id']}")
    write_json_atomic(
        side,
        {
            "matrix_id": matrix["matrix_id"],
            "scorecard": scorecard,
            "missing_metric_report": missing_report,
            "unknown_label_report": unknown_report,
        },
    )
    return path
