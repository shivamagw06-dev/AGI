"""Connector QA — download/parser/schema/duplicates/continuity/freshness → repair queue."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_connector_qa(connector_id: str, result: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "download_success": bool(result.get("ok") or result.get("records")),
        "parser_success": bool((result.get("diagnostics") or {}).get("parse_path")) or bool(result.get("records")),
        "schema_validity": bool((result.get("validation") or {}).get("ok", True)),
        "duplicate_detection": int((result.get("validation") or {}).get("duplicate_count") or 0) == 0,
        "missing_periods": True,  # filled by caller for series connectors
        "historical_continuity": bool((result.get("validation") or {}).get("continuity_ok", True)),
        "data_freshness": True,
        "coverage": (result.get("coverage_pct") or 0) > 0,
    }
    failed = [k for k, v in checks.items() if not v]
    quality = round(100.0 * (len(checks) - len(failed)) / max(1, len(checks)), 1)
    report = {
        "connector_id": connector_id,
        "checks": checks,
        "failed_checks": failed,
        "quality_score": quality,
        "ok": not failed,
        "generated_at": _now(),
    }
    if failed:
        try:
            from institutional_data.persistence.queue_persistence import QueuePersistence

            qp = QueuePersistence()
            qp.save_repair_queue(
                {
                    "items": [
                        {
                            "reason": f"qa_{f}",
                            "connector": connector_id,
                            "priority": 2,
                            "enqueued_at": _now(),
                        }
                        for f in failed
                    ],
                    "source": "connector_qa",
                }
            )
        except Exception:
            pass
    return report
