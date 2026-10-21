"""Warehouse observability counters (file-backed)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.financial_warehouse.restatements.engine import restatement_history
from financial_statements_engine.financial_warehouse.storage.roots import index_root, warehouse_root
from financial_statements_engine.util import now_iso


def warehouse_metrics() -> dict[str, Any]:
    root = warehouse_root()
    facts_n = sum(1 for _ in (root / "facts").rglob("*_v*.json")) if (root / "facts").exists() else 0
    idx_n = sum(1 for _ in index_root().rglob("*.json")) if index_root().exists() else 0
    hist_n = sum(1 for _ in (root / "history").glob("*.jsonl")) if (root / "history").exists() else 0
    return {
        "warehouse_writes_facts": facts_n,
        "index_files": idx_n,
        "history_logs": hist_n,
        "restatement_n": len(restatement_history()),
        "storage_root": str(root),
        "as_of": now_iso(),
    }
