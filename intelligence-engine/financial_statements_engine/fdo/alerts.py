"""Operational alerts for Financial Data Operations (FDO Phase 1)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.fdo.schema import ALERT_CRITICAL, ALERT_INFO, ALERT_WARNING, VERSION, WORKSTREAM_ID
from financial_statements_engine.util import now_iso


def generate_alerts(
    *,
    coverage: dict[str, Any] | None = None,
    ops: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from financial_statements_engine.fdo.coverage import universe_coverage
    from financial_statements_engine.fdo.metrics import ops_bundle

    cov = coverage or universe_coverage("gold")
    bundle = ops or ops_bundle()
    ing = bundle.get("ingestion") or {}
    wf = bundle.get("workflows") or {}
    sources = (bundle.get("sources") or {}).get("sources") or []

    alerts: list[dict[str, Any]] = []

    avg_cov = float(cov.get("average_coverage_pct") or 0.0)
    if avg_cov < 40:
        alerts.append(
            {
                "code": "COVERAGE_LOW",
                "severity": ALERT_CRITICAL,
                "message": f"Universe average coverage {avg_cov}% below 40%",
            }
        )
    elif avg_cov < 70:
        alerts.append(
            {
                "code": "COVERAGE_DROPPING",
                "severity": ALERT_WARNING,
                "message": f"Universe average coverage {avg_cov}% below 70%",
            }
        )

    dlq = int(wf.get("dlq_size") or 0)
    if dlq >= 10:
        alerts.append({"code": "DLQ_LARGE", "severity": ALERT_CRITICAL, "message": f"Dead letter queue size {dlq}"})
    elif dlq >= 1:
        alerts.append({"code": "DLQ_NONEMPTY", "severity": ALERT_WARNING, "message": f"Dead letter queue size {dlq}"})

    failed_wf = int(wf.get("failed") or 0)
    if failed_wf >= 5:
        alerts.append({"code": "WORKFLOW_FAILURES", "severity": ALERT_WARNING, "message": f"{failed_wf} failed workflows"})

    failed_dl = int(ing.get("failed_downloads") or 0)
    if failed_dl >= 5:
        alerts.append(
            {
                "code": "REPEATED_DOWNLOAD_FAILURES",
                "severity": ALERT_WARNING,
                "message": f"{failed_dl} failed downloads observed",
            }
        )

    if int(ing.get("collected_today") or 0) == 0:
        alerts.append(
            {
                "code": "NO_NEW_FILINGS",
                "severity": ALERT_WARNING,
                "message": "No filings collected today",
            }
        )

    for s in sources:
        if s.get("availability") in ("error", "disabled", "unavailable"):
            alerts.append(
                {
                    "code": "SOURCE_UNAVAILABLE",
                    "severity": ALERT_WARNING,
                    "message": f"Source {s.get('source_id')} availability={s.get('availability')}",
                    "source_id": s.get("source_id"),
                }
            )
        fail_pct = s.get("failure_pct")
        if isinstance(fail_pct, (int, float)) and fail_pct >= 50:
            alerts.append(
                {
                    "code": "SOURCE_HIGH_FAILURE",
                    "severity": ALERT_WARNING,
                    "message": f"Source {s.get('source_id')} failure_pct={fail_pct}",
                    "source_id": s.get("source_id"),
                }
            )

    if not alerts:
        alerts.append({"code": "OPS_HEALTHY", "severity": ALERT_INFO, "message": "No operational warnings"})

    return {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "n": len(alerts),
        "alerts": alerts,
        "as_of": now_iso(),
    }
