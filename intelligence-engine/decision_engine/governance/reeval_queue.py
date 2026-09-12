"""Automatic re-evaluation queue — gate failure schedules healing work."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_put(name: str, payload: dict[str, Any]) -> None:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        hd_store.put_report(name, payload)
    except Exception:
        pass


def _store_get(name: str) -> dict[str, Any] | None:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        row = hd_store.get_report(name)
        return row if isinstance(row, dict) else None
    except Exception:
        return None


def build_queued_actions(
    *,
    readiness_gate: dict[str, Any] | None = None,
    critical_missing: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    critical = critical_missing if isinstance(critical_missing, dict) else {}
    actions: list[dict[str, Any]] = []

    for item in critical.get("items") or []:
        key = str(item.get("key") or "")
        label = str(item.get("label") or key)
        if key in {"financials", "filings"}:
            actions.append(
                {
                    "action": "wait_or_ingest_quarterly_filing",
                    "label": f"Wait for / ingest {label}",
                    "priority": item.get("impact") or "High",
                    "status": "queued",
                }
            )
        elif key == "ownership":
            actions.append(
                {
                    "action": "refresh_ownership",
                    "label": "Refresh ownership / shareholding",
                    "priority": item.get("impact") or "High",
                    "status": "queued",
                }
            )
        elif key == "valuation":
            actions.append(
                {
                    "action": "refresh_valuation",
                    "label": "Refresh peer valuation",
                    "priority": item.get("impact") or "Medium",
                    "status": "queued",
                }
            )
        elif key == "technicals":
            actions.append(
                {
                    "action": "refresh_market_snapshot",
                    "label": "Refresh technical / price snapshot",
                    "priority": "Medium",
                    "status": "queued",
                }
            )
        else:
            actions.append(
                {
                    "action": f"repair_{key or 'evidence'}",
                    "label": f"Repair {label}",
                    "priority": item.get("impact") or "Medium",
                    "status": "queued",
                }
            )

    # Always re-run decision engine after evidence repair when gate failed
    if gate.get("hard_fail") or gate.get("band") in {"deferred", "watchlist"}:
        actions.append(
            {
                "action": "rerun_decision_engine",
                "label": "Re-run Decision Engine after evidence refresh",
                "priority": "High",
                "status": "queued",
            }
        )

    # Deduplicate by action id
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in actions:
        aid = str(a.get("action"))
        if aid in seen:
            continue
        seen.add(aid)
        out.append(a)
    return out[:12]


def enqueue_reevaluation(
    *,
    ticker: str | None,
    company_name: str | None = None,
    readiness_gate: dict[str, Any] | None = None,
    critical_missing: dict[str, Any] | None = None,
    recommendation_id: str | None = None,
) -> dict[str, Any]:
    """Persist a self-healing re-evaluation job when the institutional gate fails."""
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    t = (ticker or "").upper() or "UNKNOWN"
    actions = build_queued_actions(readiness_gate=gate, critical_missing=critical_missing)
    should_queue = bool(gate.get("hard_fail") or gate.get("band") in {"deferred", "watchlist"} or actions)

    job = {
        "job_id": f"REEVAL-{t}-{uuid4().hex[:8]}",
        "ticker": t,
        "company_name": company_name,
        "recommendation_id": recommendation_id,
        "queued_at": _now(),
        "status": "queued" if should_queue else "not_required",
        "gate_status": gate.get("status"),
        "readiness_band": gate.get("band"),
        "recommendation_readiness_pct": gate.get("recommendation_readiness_pct"),
        "queued_actions": actions,
        "self_healing": True,
        "note": (
            "Institutional gate failed — collectors / decision stack queued for re-evaluation."
            if should_queue
            else "Gate open — no automatic re-evaluation required."
        ),
    }

    if should_queue:
        qname = "iros_reeval_queue"
        q = _store_get(qname) or {"items": [], "updated_at": None}
        items = [i for i in (q.get("items") or []) if str(i.get("ticker") or "").upper() != t]
        items.insert(0, job)
        q["items"] = items[:500]
        q["updated_at"] = _now()
        _store_put(qname, q)
        _store_put(f"iros_reeval_{t}", job)

        # Soft-wire into institutional repair queue when available
        try:
            from institutional_data.persistence.queue_persistence import QueuePersistence

            QueuePersistence().save_repair_queue(
                {
                    "items": [
                        {
                            "company": t,
                            "reason": "iros_gate:" + ",".join(
                                str(a.get("action")) for a in actions[:4]
                            ),
                            "priority": 1,
                            "enqueued_at": _now(),
                            "job_id": job["job_id"],
                        }
                    ],
                    "source": "iros_governance",
                    "updated_at": _now(),
                }
            )
        except Exception:
            pass

    return job


def list_reeval_queue(*, limit: int = 50) -> dict[str, Any]:
    q = _store_get("iros_reeval_queue") or {"items": []}
    items = list(q.get("items") or [])[: max(1, min(limit, 200))]
    return {"items": items, "count": len(items), "updated_at": q.get("updated_at")}
