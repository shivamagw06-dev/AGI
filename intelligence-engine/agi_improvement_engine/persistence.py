"""Optional Supabase persistence for improvement evaluations (append-only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from agi_improvement_engine.store import scrub


def _supabase_config() -> tuple[str, str] | None:
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if url and key:
        return url, key
    return None


def _rest(method: str, path: str, payload: dict[str, Any] | list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cfg = _supabase_config()
    if not cfg:
        return {"ok": False, "skipped": True, "reason": "no_supabase_credentials"}
    url, key = cfg
    body = None
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    if payload is not None:
        body = json.dumps(scrub(payload), ensure_ascii=False, default=str).encode("utf-8")
    request = urllib.request.Request(f"{url}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=float(os.environ.get("AGI_SUPABASE_TIMEOUT_SEC", "20"))) as response:
            text = response.read().decode("utf-8").strip()
            if not text:
                return {"ok": True}
            return {"ok": True, "data": json.loads(text)}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        return {"ok": False, "status": exc.code, "error": detail}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}


def save_session_report(report: dict[str, Any], *, endpoint: str = "") -> dict[str, Any]:
    host = ""
    if endpoint:
        try:
            host = urllib.parse.urlparse(endpoint).netloc
        except Exception:  # noqa: BLE001
            host = endpoint[:120]
    row = {
        "session_id": report.get("session_id"),
        "version": report.get("version"),
        "mode": report.get("mode", "execute"),
        "endpoint_host": host or None,
        "started_questions": int(report.get("started_questions") or 0),
        "completed": int(report.get("completed") or 0),
        "passed": int(report.get("passed") or 0),
        "failed": int(report.get("failed") or 0),
        "pass_rate": report.get("pass_rate"),
        "average_score": report.get("average_score"),
        "critical_failures": int(report.get("critical_failures") or 0),
        "average_latency_ms": report.get("average_latency_ms"),
        "model_calls": int(report.get("model_calls") or 0),
        "input_tokens": int(report.get("input_tokens") or 0),
        "output_tokens": int(report.get("output_tokens") or 0),
        "total_tokens": int(report.get("total_tokens") or 0),
        "estimated_api_cost_usd": report.get("estimated_api_cost_usd"),
        "report": report,
        "finished_at": report.get("finished_at"),
    }
    return _rest("POST", "/rest/v1/agi_improvement_sessions", row)


def save_evaluation_row(row: dict[str, Any]) -> dict[str, Any]:
    question = row.get("question") or {}
    score = row.get("score") or {}
    payload = {
        "session_id": row.get("session_id"),
        "question_id": question.get("question_id"),
        "ticker": question.get("ticker"),
        "sector": question.get("sector"),
        "difficulty": question.get("difficulty"),
        "kind": question.get("kind"),
        "status": row.get("status"),
        "latency_ms": row.get("latency_ms"),
        "score": score.get("score"),
        "passed": bool(score.get("passed")),
        "critical_failure": bool(score.get("critical_failure")),
        "root_causes": score.get("root_causes") or [],
        "record": row,
    }
    return _rest("POST", "/rest/v1/agi_improvement_evaluations", payload)


def save_learning_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "event_id": event.get("event_id"),
        "session_id": event.get("session_id"),
        "status": event.get("status", "DIAGNOSIS_REQUIRED"),
        "root_causes": event.get("root_causes") or [],
        "critical_failures": event.get("critical_failures") or [],
        "affected_subsystem": event.get("affected_subsystem"),
        "record": event,
    }
    return _rest("POST", "/rest/v1/agi_improvement_learning_events", payload)
