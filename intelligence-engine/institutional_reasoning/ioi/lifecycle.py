"""Module 1 — Decision Lifecycle.

Every recommendation becomes a durable object. Nothing disappears.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from institutional_reasoning.ioi.schema import IOI_VERSION

LIFECYCLE_VERSION = "decision-lifecycle-v1.0.0"

_STORE: dict[str, dict[str, Any]] = {}


def reset_lifecycle() -> None:
    _STORE.clear()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def register_decision(
    ipi_decision: dict[str, Any],
    *,
    research_record: dict[str, Any] | None = None,
    benchmark: str = "NIFTY50",
    horizon_days: int = 90,
) -> dict[str, Any]:
    """Create a lifecycle object from an IPI portfolio decision."""
    research_record = research_record or {}
    decision_id = f"dec_{uuid.uuid4().hex[:16]}"
    rec = ipi_decision.get("recommendation") or {}
    committee = ipi_decision.get("committee") or {}
    sizing = ipi_decision.get("sizing") or {}
    scenarios = ipi_decision.get("scenarios") or {}
    pdg = ipi_decision.get("portfolio_decision_graph") or {}
    djg_ref = ipi_decision.get("djg_reference") or (research_record.get("justification_graph") or {}).get("run_id")
    research_djg = research_record.get("justification_graph") or {}

    decision_date = _now()
    review_dates = [
        (datetime.now(timezone.utc) + timedelta(days=d)).date().isoformat()
        for d in (30, 60, horizon_days)
    ]

    withheld = bool(ipi_decision.get("withheld") or committee.get("action") == "Withhold")
    obj = {
        "lifecycle_version": LIFECYCLE_VERSION,
        "ioi_version": IOI_VERSION,
        "decision_id": decision_id,
        "status": "withheld" if withheld else "open",
        "decision": {
            "action": committee.get("action") or sizing.get("action"),
            "conclusion": committee.get("conclusion") or rec.get("conclusion"),
            "conviction": committee.get("conviction") or sizing.get("conviction"),
            "confidence": committee.get("confidence") or sizing.get("confidence"),
        },
        "research_djg": djg_ref or research_djg.get("run_id"),
        "research_djg_integrity": (research_djg.get("integrity") or {}).get("valid"),
        "portfolio_djg": pdg.get("run_id") or ipi_decision.get("run_id"),
        "portfolio_djg_integrity": (pdg.get("integrity") or {}).get("valid"),
        "pdg": {"run_id": pdg.get("run_id"), "integrity": pdg.get("integrity")},
        "ticker": ipi_decision.get("entity_id"),
        "entity_name": ipi_decision.get("entity_name"),
        "position_weight": sizing.get("target_weight") if sizing.get("target_weight") is not None else rec.get("target_weight"),
        "current_weight": sizing.get("current_weight"),
        "expected_return": sizing.get("expected_return")
        or (ipi_decision.get("portfolio_evidence") or {}).get("expected_return"),
        "expected_downside": sizing.get("expected_downside")
        or (ipi_decision.get("portfolio_evidence") or {}).get("expected_downside"),
        "scenario": (scenarios.get("scenarios") or {}).get("base") or {},
        "scenarios": scenarios.get("scenarios") or {},
        "shocks": scenarios.get("shocks") or [],
        "decision_date": decision_date,
        "review_dates": review_dates,
        "horizon_days": horizon_days,
        "benchmark": benchmark,
        "frameworks": deepcopy(research_record.get("frameworks") or []),
        "policy": deepcopy(ipi_decision.get("policy") or {}),
        "risk": deepcopy(ipi_decision.get("risk") or {}),
        "exposure": deepcopy(ipi_decision.get("exposure") or {}),
        "ipi_run_id": ipi_decision.get("run_id"),
        "research_run_id": ipi_decision.get("research_run_id") or research_record.get("run_id"),
        "withheld": withheld,
        "created_at": decision_date,
        "updated_at": decision_date,
    }
    _STORE[decision_id] = obj
    return deepcopy(obj)


def get_decision(decision_id: str) -> dict[str, Any] | None:
    row = _STORE.get(decision_id)
    return deepcopy(row) if row else None


def update_decision(decision_id: str, **fields: Any) -> dict[str, Any] | None:
    row = _STORE.get(decision_id)
    if not row:
        return None
    row.update(fields)
    row["updated_at"] = _now()
    return deepcopy(row)


def list_decisions(*, status: str | None = None, ticker: str | None = None) -> list[dict[str, Any]]:
    out = []
    for row in _STORE.values():
        if status and row.get("status") != status:
            continue
        if ticker and str(row.get("ticker") or "").upper() != str(ticker).upper():
            continue
        out.append(deepcopy(row))
    return out


def store_snapshot() -> dict[str, Any]:
    return {
        "lifecycle_version": LIFECYCLE_VERSION,
        "count": len(_STORE),
        "open": sum(1 for r in _STORE.values() if r.get("status") == "open"),
        "evaluated": sum(1 for r in _STORE.values() if r.get("status") == "evaluated"),
        "withheld": sum(1 for r in _STORE.values() if r.get("status") == "withheld"),
    }
