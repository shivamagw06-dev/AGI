"""IDO Mission Control dashboard."""

from __future__ import annotations

from typing import Any

from institutional_decision_office import store as decision_store
from institutional_decision_office.schema import (
    COMPANY,
    DECISION_SCHEMA_VERSION,
    IDO_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
)


def build_board() -> dict[str, Any]:
    tel = decision_store.telemetry_snapshot()
    waiting = decision_store.list_decisions(decision="Wait", limit=50)
    monitor = decision_store.list_decisions(decision="Monitor", limit=50)
    approve = decision_store.list_decisions(decision="Approve", limit=50)
    earnings = decision_store.list_decisions(review_trigger="earnings", limit=50)
    escalate = decision_store.list_decisions(decision="Escalate", limit=50)
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "programme": PROGRAMME,
        "version": IDO_VERSION,
        "schema_version": DECISION_SCHEMA_VERSION,
        "release": "AGI v4.0",
        "n_decisions": tel.get("n_decisions"),
        "decision_distribution": tel.get("decision_distribution"),
        "lifecycle_distribution": tel.get("lifecycle_distribution"),
        "n_wait": len(waiting),
        "n_monitor": len(monitor),
        "n_approve": len(approve),
        "n_escalate": len(escalate),
        "review_after_earnings": [
            {
                "decision_id": d.get("decision_id"),
                "thesis_id": d.get("thesis_id"),
                "company": d.get("company"),
                "review_date": d.get("review_date"),
            }
            for d in earnings[:10]
        ],
        "recent": tel.get("recent"),
        "orders": False,
        "buy_sell": False,
        "execution": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }
