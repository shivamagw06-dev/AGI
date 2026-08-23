"""Read-only admin dashboard payload for Pricing Engine V1 validation."""

from __future__ import annotations

import json
from datetime import datetime, time as clock_time, timezone
from typing import Any

from .store import OptionEvidenceStore
from .upstox_live import IST, LiveConfig


MARKET_OPEN = clock_time(9, 15)
MARKET_CLOSE = clock_time(15, 30)


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _row(row: Any) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validation_dashboard() -> dict[str, Any]:
    """Return sanitized collector and report state; never return quotes or tokens."""
    config = LiveConfig.from_environment()
    store = OptionEvidenceStore(config.database_path)
    with store.connect() as connection:
        latest_run = _row(
            connection.execute(
                """
                SELECT run_id, started_at, completed_at, status,
                       expiries_json, counts_json, error
                FROM collector_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
        )
        snapshot = _row(
            connection.execute(
                """
                SELECT COUNT(*) AS snapshots,
                       COUNT(DISTINCT instrument_key) AS contracts,
                       MIN(captured_at) AS first_captured_at,
                       MAX(captured_at) AS latest_captured_at
                FROM option_snapshots
                """
            ).fetchone()
        ) or {}
        observations = _row(
            connection.execute(
                """
                SELECT COUNT(*) AS observations,
                       COUNT(DISTINCT local_date) AS trading_days,
                       MAX(observed_at) AS latest_observed_at
                FROM validation_observations
                """
            ).fetchone()
        ) or {}
        coverage = [
            dict(item)
            for item in connection.execute(
                """
                SELECT expiry, option_type,
                       COUNT(DISTINCT instrument_key) AS contracts,
                       COUNT(*) AS snapshots
                FROM option_snapshots
                GROUP BY expiry, option_type
                ORDER BY expiry, option_type
                """
            ).fetchall()
        ]
        latest_report_row = _row(
            connection.execute(
                """
                SELECT report_date, generated_at, status, report_json
                FROM daily_reports
                ORDER BY report_date DESC
                LIMIT 1
                """
            ).fetchone()
        )
        recent_report_rows = [
            dict(item)
            for item in connection.execute(
                """
                SELECT report_date, generated_at, status, report_json
                FROM daily_reports
                ORDER BY report_date DESC
                LIMIT 20
                """
            ).fetchall()
        ]

    if latest_run:
        latest_run["expiries"] = _json(latest_run.pop("expiries_json"), [])
        latest_run["counts"] = _json(latest_run.pop("counts_json"), {})
        if latest_run.get("error"):
            latest_run["error"] = str(latest_run["error"])[:300]

    now = datetime.now(timezone.utc)
    local = now.astimezone(IST)
    market_session = (
        local.weekday() < 5
        and MARKET_OPEN <= local.time().replace(tzinfo=None) <= MARKET_CLOSE
    )
    last_capture = _parse_timestamp(snapshot.get("latest_captured_at"))
    freshness_minutes = (
        max(0.0, (now - last_capture.astimezone(timezone.utc)).total_seconds() / 60.0)
        if last_capture
        else None
    )
    if latest_run and latest_run.get("status") != "success":
        worker_status = "error"
    elif market_session and (freshness_minutes is None or freshness_minutes > 25):
        worker_status = "stale"
    elif market_session:
        worker_status = "collecting"
    else:
        worker_status = "waiting_for_market"

    latest_report = None
    if latest_report_row:
        latest_report = {
            "report_date": latest_report_row["report_date"],
            "generated_at": latest_report_row["generated_at"],
            "status": latest_report_row["status"],
            "report": _json(latest_report_row["report_json"], {}),
        }
    recent_reports = []
    for report_row in recent_report_rows:
        report = _json(report_row["report_json"], {})
        recent_reports.append(
            {
                "report_date": report_row["report_date"],
                "generated_at": report_row["generated_at"],
                "status": report_row["status"],
                "daily": report.get("daily") or {},
                "cumulative": report.get("cumulative") or {},
            }
        )

    return {
        "ok": True,
        "admin_only": True,
        "research_only": True,
        "execution_enabled": False,
        "generated_at": now.isoformat(),
        "model": {
            "name": "Pricing Engine V1",
            "status": (
                (latest_report or {}).get("status")
                or "extended_validation_pending"
            ),
            "claim_boundary": "conditional repricing, not direction or profitability",
            "minimum_validation_days": 60,
            "acceptance_mape_pct": 3.0,
            "specification": "frozen",
        },
        "worker": {
            "status": worker_status,
            "market_session": market_session,
            "market_local_time": local.isoformat(),
            "freshness_minutes": freshness_minutes,
            "latest_run": latest_run,
        },
        "evidence": {
            **snapshot,
            **observations,
            "coverage": coverage,
        },
        "latest_report": latest_report,
        "recent_reports": recent_reports,
    }
