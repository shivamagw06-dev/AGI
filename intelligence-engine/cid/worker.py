"""Continuous, version-aware company dossier population service."""

from __future__ import annotations

import json
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any

from cid.openai_dossier import status as openai_status
from cid.persistence import generated_age_seconds, latest_versions
from cid.openai_dossier import GENERATOR_VERSION, generate

STOP = Event()
DEFAULT_WORKERS = 4
MAX_WORKERS = 15
DEFAULT_SPRINT_MODE = False
# Operational kill switch. Keep the dossier campaign stopped until a deliberate
# code review re-enables it; Render may retain older Blueprint environment values.
CAMPAIGN_FORCE_PAUSED = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_path() -> Path:
    root = Path(os.environ.get("KIP_DATA_DIR") or "/tmp")
    root.mkdir(parents=True, exist_ok=True)
    return root / "cid_dossier_worker_status.json"


def write_status(payload: dict[str, Any]) -> None:
    path = _status_path()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({**payload, "updated_at": _now()}, indent=2, default=str))
    temp.replace(path)


def read_status() -> dict[str, Any]:
    paused = CAMPAIGN_FORCE_PAUSED or os.environ.get("CID_DOSSIER_PAUSED", "true").strip().lower() in {"1", "true", "yes"}
    enabled = os.environ.get("CID_DOSSIER_WORKER_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    try:
        payload = json.loads(_status_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        payload = {"status": "not_started", "workers": 0}

    updated_at = str(payload.get("updated_at") or "")
    age_seconds: float | None = None
    try:
        age_seconds = max(
            0.0,
            (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            ).total_seconds(),
        )
    except (TypeError, ValueError):
        pass

    if paused or not enabled:
        return {
            **payload,
            "status": "paused" if paused else "disabled",
            "workers": 0,
            "active": [],
            "configured_enabled": enabled,
            "configured_paused": paused,
            "snapshot_age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
            "snapshot_stale": True,
        }
    return {
        **payload,
        "configured_enabled": enabled,
        "configured_paused": paused,
        "snapshot_age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
        "snapshot_stale": age_seconds is None or age_seconds > 900,
    }


def warehouse_universe() -> list[str]:
    from institutional_warehouse import store

    symbols = store.entities("company_master")
    return sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})


def eligible_queue(*, refresh_days: float) -> tuple[list[str], int]:
    universe = warehouse_universe()
    versions = latest_versions()
    fresh_seconds = max(0.25, refresh_days) * 86400
    legacy: list[str] = []
    missing: list[str] = []
    stale: list[str] = []
    fresh = 0
    for ticker in universe:
        version = versions.get(ticker) or {}
        age = generated_age_seconds(version)
        current_spec = str(version.get("generator_version") or "") == GENERATOR_VERSION
        if current_spec and age is not None and age < fresh_seconds:
            fresh += 1
        elif version and not current_spec:
            legacy.append(ticker)
        elif not version:
            missing.append(ticker)
        else:
            stale.append(ticker)
    return legacy + missing + stale, fresh


def _generate(ticker: str) -> dict[str, Any]:
    started = time.monotonic()
    from cid.warehouse_dossier import build

    dossier = build(ticker)
    if os.environ.get("CID_DOSSIER_LIVE_ENRICHMENT_ENABLED", "true").strip().lower() in {"1", "true", "yes"}:
        try:
            from ecp.production import soft_complete

            completion = soft_complete(
                query=f"Complete institutional dossier evidence for {ticker}",
                ticker=ticker,
                cid=dossier,
                force=True,
            )
            delta = completion.get("cid_delta") if isinstance(completion.get("cid_delta"), dict) else {}
            for key, value in delta.items():
                if key not in {"ticker", "ecp_completed"} and value not in (None, {}, []):
                    dossier[key] = value
            dossier["evidence_completion"] = {
                key: completion.get(key)
                for key in (
                    "coverage_before",
                    "coverage",
                    "completed_automatically",
                    "still_missing",
                    "still_missing_items",
                    "providers_used",
                    "conflicts",
                    "quality_panel",
                    "errors",
                )
            }
        except Exception as exc:
            dossier["evidence_completion"] = {
                "status": "degraded",
                "error": type(exc).__name__,
                "message": str(exc)[:300],
            }
    openai_enabled = os.environ.get("CID_OPENAI_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    if openai_enabled:
        result = generate(ticker, dossier)
    else:
        result = {"ok": False, "error": "openai_generation_disabled"}
    if not result.get("ok"):
        from cid.learning import compose, readiness

        allow_fallback = os.environ.get("CID_DOSSIER_ALLOW_FALLBACK", "false").strip().lower() in {"1", "true", "yes"}
        if allow_fallback and readiness().get("ready"):
            reason = ": ".join(
                value for value in (
                    str(result.get("error") or "openai_unavailable"),
                    str(result.get("error_type") or ""),
                    str(result.get("message") or ""),
                ) if value
            )
            result = compose(ticker, dossier, reason=reason)
    persisted = (result.get("persistence") or {}).get("persisted")
    if result.get("ok") and not persisted:
        return {
            "ok": False,
            "ticker": ticker,
            "error": "dossier_not_persisted",
            "detail": result.get("persistence"),
            "runtime_seconds": round(time.monotonic() - started, 2),
        }
    return {
        "ok": bool(result.get("ok")),
        "ticker": ticker,
        "error": result.get("error"),
        "message": result.get("message"),
        "version": (result.get("persistence") or {}).get("version"),
        "fallback": bool(result.get("fallback")),
        "error_type": result.get("error_type"),
        "message": result.get("message"),
        "runtime_seconds": round(time.monotonic() - started, 2),
    }


def run_forever() -> None:
    if CAMPAIGN_FORCE_PAUSED:
        write_status({
            "status": "paused",
            "workers": 0,
            "active": [],
            "reason": "campaign_force_paused",
        })
        return
    sprint_default = "true" if DEFAULT_SPRINT_MODE else "false"
    sprint_mode = os.environ.get("CID_DOSSIER_SPRINT_MODE", sprint_default).strip().lower() in {"1", "true", "yes"}
    configured_workers = MAX_WORKERS if sprint_mode else int(os.environ.get("CID_DOSSIER_WORKERS", str(DEFAULT_WORKERS)))
    workers = max(1, min(MAX_WORKERS, configured_workers))
    refresh_days = float(os.environ.get("CID_DOSSIER_REFRESH_DAYS", "30"))
    idle_seconds = max(30, int(os.environ.get("CID_DOSSIER_IDLE_SECONDS", "300")))
    batch_pause_seconds = max(0, float(os.environ.get("CID_DOSSIER_BATCH_PAUSE_SECONDS", "10")))
    failures: dict[str, dict[str, Any]] = {}
    completed_tickers: set[str] = set()
    completed = 0
    fallback_completed = 0

    write_status({
        "status": "starting",
        "workers": workers,
        "refresh_days": refresh_days,
        "batch_pause_seconds": batch_pause_seconds,
        "sprint_mode": sprint_mode,
    })
    while not STOP.is_set():
        llm = openai_status()
        if not llm.get("enabled") and not (llm.get("agi_takeover") or {}).get("ready"):
            write_status({"status": "waiting_for_openai_or_learned_profile", "workers": workers, "openai": llm})
            STOP.wait(idle_seconds)
            continue
        try:
            queue, fresh = eligible_queue(refresh_days=refresh_days)
        except Exception as exc:
            write_status({"status": "degraded", "workers": workers, "error": str(exc)[:400]})
            STOP.wait(idle_seconds)
            continue

        now = time.time()
        queue = [
            ticker for ticker in queue
            if ticker not in completed_tickers
            and now >= float((failures.get(ticker) or {}).get("retry_at") or 0)
        ]
        if not queue:
            write_status(
                {
                    "status": "idle",
                    "workers": workers,
                    "universe": fresh,
                    "fresh": fresh,
                    "queued": 0,
                    "completed_this_process": completed,
                    "fallback_completed_this_process": fallback_completed,
                    "agi_takeover": llm.get("agi_takeover"),
                    "failures": len(failures),
                    "recent_failures": [
                        {"ticker": ticker, **detail}
                        for ticker, detail in list(failures.items())[-8:]
                    ],
                }
            )
            STOP.wait(idle_seconds)
            continue

        batch = queue[:workers]
        write_status(
            {
                "status": "running",
                "workers": workers,
                "universe": len(queue) + fresh,
                "fresh": fresh,
                "queued": len(queue),
                "active": batch,
                "completed_this_process": completed,
                "fallback_completed_this_process": fallback_completed,
                "agi_takeover": llm.get("agi_takeover"),
                "failures": len(failures),
                "recent_failures": [
                    {"ticker": ticker, **detail}
                    for ticker, detail in list(failures.items())[-8:]
                ],
            }
        )
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cid-dossier") as pool:
            futures = {pool.submit(_generate, ticker): ticker for ticker in batch}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"ok": False, "ticker": ticker, "error": type(exc).__name__, "message": str(exc)[:300]}
                if result.get("ok"):
                    completed += 1
                    completed_tickers.add(ticker)
                    if result.get("fallback"):
                        fallback_completed += 1
                    failures.pop(ticker, None)
                else:
                    attempts = int((failures.get(ticker) or {}).get("attempts") or 0) + 1
                    failures[ticker] = {
                        "attempts": attempts,
                        "error": result.get("error"),
                        "message": result.get("message"),
                        "retry_at": time.time() + min(21600, 60 * (2 ** min(attempts, 8))),
                    }
        if batch_pause_seconds and not STOP.is_set():
            write_status(
                {
                    "status": "yielding",
                    "workers": workers,
                    "fresh": fresh,
                    "queued": max(0, len(queue) - len(batch)),
                    "completed_this_process": completed,
                    "fallback_completed_this_process": fallback_completed,
                    "failures": len(failures),
                    "batch_pause_seconds": batch_pause_seconds,
                }
            )
            STOP.wait(batch_pause_seconds)


def stop(*_: Any) -> None:
    STOP.set()


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    run_forever()


if __name__ == "__main__":
    main()
