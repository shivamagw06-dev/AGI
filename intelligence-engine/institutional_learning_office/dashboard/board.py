"""ILO Mission Control dashboard."""

from __future__ import annotations

from typing import Any

from institutional_learning_office import store as learning_store
from institutional_learning_office.schema import (
    COMPANY,
    ILO_VERSION,
    LEARNING_CATEGORIES,
    LEARNING_SCHEMA_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
)


def build_board() -> dict[str, Any]:
    store = learning_store.get_learning_store()
    tel = store.telemetry_snapshot()
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "programme": PROGRAMME,
        "version": ILO_VERSION,
        "schema_version": LEARNING_SCHEMA_VERSION,
        "release": "AGI v4.0",
        "final_office_module": True,
        "n_learnings": tel.get("learnings"),
        "by_category": tel.get("by_category"),
        "by_outcome": tel.get("by_outcome"),
        "theses_covered": tel.get("theses_covered"),
        "categories": list(LEARNING_CATEGORIES),
        "recent": tel.get("recent"),
        "knowledge_factory_updated": False,
        "process_memory_only": True,
        "mutates_thesis": False,
        "positions": False,
        "orders": False,
        "execution": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }
