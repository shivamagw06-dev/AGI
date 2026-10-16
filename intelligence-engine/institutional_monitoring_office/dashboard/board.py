"""IMO Mission Control dashboard."""

from __future__ import annotations

from typing import Any

from institutional_monitoring_office import store as event_store
from institutional_monitoring_office.schema import (
    COMPANY,
    EVENT_SCHEMA_VERSION,
    IMO_VERSION,
    MODULE_CODE,
    MONITOR_DOMAINS,
    PRODUCT_LINE,
    PROGRAMME,
)


def build_board() -> dict[str, Any]:
    store = event_store.get_monitoring_store()
    tel = store.telemetry_snapshot()
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "programme": PROGRAMME,
        "version": IMO_VERSION,
        "schema_version": EVENT_SCHEMA_VERSION,
        "release": "AGI v4.0",
        "n_events": tel.get("events"),
        "requires_review": tel.get("requires_review"),
        "ideas_covered": tel.get("ideas_covered"),
        "by_severity": tel.get("by_severity"),
        "by_recommended_action": tel.get("by_recommended_action"),
        "by_domain": tel.get("by_domain"),
        "domains_monitored": list(MONITOR_DOMAINS),
        "review_queue": tel.get("review_queue"),
        "recent": tel.get("recent"),
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "positions": False,
        "orders": False,
        "execution": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }
