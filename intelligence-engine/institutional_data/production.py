"""Institutional data production dashboard — extends CGL ops without redesign."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from institutional_data import PLATFORM_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dashboard() -> dict[str, Any]:
    from institutional_data.connectors.registry import all_connectors, get_connector
    from institutional_data.kpis import production_kpis
    from institutional_data.persistence.resume import ResumeManager
    from institutional_data.reliability.scores import reliability_dashboard
    from knowledge_factory.historical_depth import living_universe

    resume = ResumeManager()
    # Recovery runs during backfill cycles; dashboard only reports last recovery status
    try:
        recovery = (resume.ck.load(resume.RUN_CK) or {}).get("last_recovery") or {"resumed": False}
    except Exception as exc:  # noqa: BLE001
        recovery = {"error": str(exc)[:160]}

    connectors = []
    for c in all_connectors():
        try:
            connectors.append({**c.health(), **c.coverage()})
        except Exception as exc:  # noqa: BLE001
            connectors.append({"connector_id": c.connector_id, "error": str(exc)[:120]})

    living: dict[str, Any] = {}
    try:
        living = living_universe.living_universe_board() or {}
    except Exception:
        living = {}

    return {
        "platform_version": PLATFORM_VERSION,
        "generated_at": _now(),
        "kpis": production_kpis(),
        "connectors": connectors,
        "source_reliability_trends": reliability_dashboard(),
        "financial_coverage": get_connector("financial_statements").coverage(),
        "shareholding_coverage": get_connector("shareholding").coverage(),
        "ir_coverage": get_connector("company_ir").coverage(),
        "checkpoint_status": resume.status(),
        "recovery": recovery,
        "persistent_queue": resume.qp.load_queue().get("updated_at"),
        "living_universe": {
            "listed": living.get("listed_count") or living.get("universe_n"),
            "new_listings": living.get("new_listings_recent") or living.get("new_listings"),
            "delisted": living.get("delisted_count") or living.get("delisted"),
            "pending_ipos": living.get("pending_ipos_count") or living.get("pending_ipos"),
        },
        "focus": "production-grade data reliability",
    }
