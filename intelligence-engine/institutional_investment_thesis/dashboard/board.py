"""ITE Mission Control dashboard."""

from __future__ import annotations

from typing import Any

from institutional_investment_thesis import store as thesis_store
from institutional_investment_thesis.schema import (
    COMPANY,
    ITE_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
    THESIS_SCHEMA_VERSION,
)


def build_board() -> dict[str, Any]:
    tel = thesis_store.telemetry_snapshot()
    active = thesis_store.list_theses(status="ACTIVE", limit=100)
    watch = thesis_store.list_theses(decision_status="Watch", limit=100)
    waiting_earnings = thesis_store.list_theses(waiting_for="earnings", limit=50)
    dropped = thesis_store.list_theses(confidence_drop_gt=10.0, limit=50)
    confs = [float(t.get("confidence") or 0) for t in active if t.get("confidence") is not None]
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "programme": PROGRAMME,
        "version": ITE_VERSION,
        "schema_version": THESIS_SCHEMA_VERSION,
        "release": "AGI v4.0",
        "n_theses": tel.get("n_theses"),
        "lifecycle_distribution": tel.get("lifecycle_distribution"),
        "decision_distribution": tel.get("decision_distribution"),
        "n_active": len(active),
        "n_watch": len(watch),
        "average_confidence_active": round(sum(confs) / len(confs), 2) if confs else None,
        "waiting_for_earnings_review": [
            {"thesis_id": t.get("thesis_id"), "company": t.get("company"), "confidence": t.get("confidence")}
            for t in waiting_earnings[:10]
        ],
        "confidence_dropped_gt_10": [
            {
                "thesis_id": t.get("thesis_id"),
                "company": t.get("company"),
                "confidence": t.get("confidence"),
                "confidence_change": t.get("confidence_change"),
            }
            for t in dropped[:10]
        ],
        "recent": tel.get("recent"),
        "buy_sell": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }
