#!/usr/bin/env python3
"""Capture a live Ask product baseline — always writes, never overwrites, exits cleanly.

Writes after EVERY prompt (partial reports survive hangs).

Usage:
  cd intelligence-engine
  ASK_TEST_MODE=live \\
  ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \\
    python3 -m ask_product_test.run_baseline

Notes:
  - Does NOT increase production timeouts.
  - Uses ASK_TEST_LATENCY_MS only as the client wait budget (default = gateway default).
  - Artifacts: ask_test_report_pre_ikl_<UTC>.json (+ stable pointer copy when safe).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ask_product_test.harness import (
    AskProductHarness,
    _comparison_metrics,
    _artifacts_dir,
    print_health_summary,
)
from ask_product_test.prompts import (
    CONTEXT_ISOLATION_SEQUENCE,
    IKL_PROMPTS,
    SMOKE_PROMPTS,
    UNKNOWN_COMPANY_PROMPT,
)
from ask_product_test.harness import cio_cases_from_frozen


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _limit(cases: List[dict]) -> List[dict]:
    raw = os.environ.get("ASK_TEST_REGRESSION_LIMIT", "5").strip()
    try:
        n = max(1, int(raw))
    except ValueError:
        n = 5
    return cases[:n]


def _truthy(name: str, default: str = "1") -> bool:
    return str(os.environ.get(name, default) or default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _print_execution_trace(row: Dict[str, Any], orch: Dict[str, Any]) -> None:
    trace = orch.get("execution_trace")
    if isinstance(trace, str) and trace.strip():
        print(trace, flush=True)
        return
    funnel = orch.get("funnel") or orch.get("evidence") or row.get("funnel") or {}
    lat = orch.get("latency") or {}
    ent = orch.get("entity") or {}
    name = ent.get("name") or row.get("entity") or "—"
    conf = ent.get("confidence")
    if conf is None:
        conf = row.get("entity_confidence")
    conf_s = f"{float(conf):.2f}" if isinstance(conf, (int, float)) else str(conf or "—")
    ikl_ms = lat.get("ikl_ms") or 0
    reasoning_ms = lat.get("reasoning_ms") or 0
    assembly_ms = lat.get("assembly_ms") or 0
    elapsed = orch.get("elapsed_ms") or row.get("latency_ms") or lat.get("total_ms") or 0
    print(
        "\n".join(
            [
                f"Ask Trace ID: {orch.get('ask_trace_id') or row.get('ask_trace_id') or '—'}",
                f"Entity: {name} ({conf_s})",
                f"IKL: {int(ikl_ms)}ms",
                f"Retrieved: {funnel.get('retrieved', 0)}",
                f"Ranked: {funnel.get('ranked', 0)}",
                f"Passed: {funnel.get('passed', 0)}",
                f"Referenced: {funnel.get('referenced', 0)}",
                f"Reasoning: {float(reasoning_ms) / 1000:.1f}s",
                f"Assembly: {int(assembly_ms)}ms",
                f"Completed: {str(bool(orch.get('completed', row.get('completed')))).lower()}",
                f"Last completed stage: {orch.get('last_completed_stage') or lat.get('last_completed_stage') or '—'}",
                f"Elapsed: {float(elapsed) / 1000:.1f}s",
                f"Timeout: {str(bool(orch.get('timeout') or row.get('timeout'))).lower()}",
                f"Fallback: {str(bool(orch.get('fallback_used') or row.get('fallback_used'))).lower()}",
                "",
            ]
        ),
        flush=True,
    )


def _write_atomic(path: Path, report: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _enrich_row(row: Dict[str, Any], transport: Dict[str, Any]) -> Dict[str, Any]:
    payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
    orch = {}
    if isinstance(payload, dict):
        orch = payload.get("ask_orchestration") or {}
        if not orch and isinstance(payload.get("degradation"), dict):
            orch = payload["degradation"].get("ask_orchestration") or {}
    timed_out = bool(
        orch.get("timeout")
        or transport.get("timeout")
        or (
            transport.get("error")
            and "timeout" in str(transport.get("error") or "").lower()
        )
        or (
            isinstance(payload.get("detail"), str)
            and "timeout" in payload["detail"].lower()
        )
    )
    completed = bool(orch.get("completed")) if "completed" in orch else (
        bool(row.get("completed")) and not timed_out and not orch.get("partial")
    )
    if timed_out:
        completed = False
    row = {
        **row,
        "completed": completed,
        "timeout": timed_out,
        "last_completed_stage": orch.get("last_completed_stage")
        or (orch.get("latency") or {}).get("last_completed_stage"),
        "elapsed_ms": orch.get("elapsed_ms") or row.get("latency_ms"),
        "ask_trace_id": orch.get("ask_trace_id") or row.get("ask_trace_id"),
        "engine_reached": orch.get("engine_reached"),
        "fallback_used": bool(orch.get("fallback_used") or orch.get("fallback") or row.get("fallback_used")),
        "execution_trace": orch.get("execution_trace"),
        "stage_warnings": orch.get("stage_warnings")
        or (orch.get("latency") or {}).get("warnings")
        or [],
        "funnel": orch.get("funnel") or orch.get("evidence") or row.get("funnel"),
        "orchestration_latency": orch.get("latency") or row.get("orchestration_latency"),
    }
    return row


def main() -> int:
    # Client wait only — do not raise production ASK_ENGINE_TIMEOUT_MS.
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or os.environ.get("ASK_ENGINE_TIMEOUT_MS") or "120000")
    h = AskProductHarness(latency_budget_ms=latency)
    stamp = _stamp()
    out_dir = _artifacts_dir()
    primary = out_dir / f"ask_test_report_pre_ikl_{stamp}.json"
    # Never overwrite an existing file — bump suffix if needed
    if primary.exists():
        primary = out_dir / f"ask_test_report_pre_ikl_{stamp}_{os.getpid()}.json"

    cases: List[Dict[str, Any]] = []
    cases.extend(list(SMOKE_PROMPTS))
    if _truthy("ASK_TEST_INCLUDE_REGRESSION", "1"):
        cases.extend(_limit(cio_cases_from_frozen()))
        cases.append(dict(UNKNOWN_COMPANY_PROMPT))
        cases.extend(list(CONTEXT_ISOLATION_SEQUENCE))
    if _truthy("ASK_TEST_INCLUDE_IKL", "1"):
        # Soft IKL for pre-deploy baseline
        os.environ.pop("ASK_TEST_IKL_STRICT", None)
        cases.extend(list(IKL_PROMPTS))

    print(
        f"[baseline] mode={h.mode} base={h.base_url} "
        f"latency_budget_ms={latency} cases={len(cases)} out={primary}",
        flush=True,
    )

    questions: List[Dict[str, Any]] = []
    previous_entities: List[str] = []

    def flush(partial: bool = True) -> None:
        passed = sum(1 for q in questions if q.get("pass"))
        total = len(questions)
        latencies = [q.get("latency_ms") or 0 for q in questions]
        report = {
            "suite": "Founder live baseline (pre/post IKL)",
            "timestamp": _ts(),
            "mode": h.mode,
            "base_url": h.base_url,
            "latency_budget_ms": latency,
            "partial": partial,
            "completed": not partial,
            "pass_rate": (passed / total) if total else 0.0,
            "passed": passed,
            "total": total,
            "planned_total": len(cases),
            "average_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
            "questions": questions,
            "comparison_metrics": _comparison_metrics(questions),
            "artifact": str(primary),
            "note": (
                "Incremental baseline — written after every prompt. "
                "Never overwrites prior stamped reports."
            ),
        }
        _write_atomic(primary, report)
        # Also mirror under /opt/cursor/artifacts when present (stamped — no overwrite)
        try:
            opt = Path("/opt/cursor/artifacts")
            if opt.is_dir():
                _write_atomic(opt / primary.name, report)
        except Exception:
            pass
        return report

    cooldown_s = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "10") or "10")
    for idx, case in enumerate(cases, 1):
        if idx > 1 and cooldown_s > 0 and h.mode == "live":
            # Avoid Render Starter 502 cascades between heavy Ask cases.
            time.sleep(cooldown_s)
        isolate = str(case.get("id") or "").startswith("CTX-")
        print(
            f"\n[baseline] ({idx}/{len(cases)}) {case.get('id')} — {case.get('prompt')[:100]}",
            flush=True,
        )
        t0 = time.perf_counter()
        try:
            transport = h.ask(case["prompt"], ticker=case.get("ticker"), case=case)
        except Exception as exc:  # noqa: BLE001
            transport = {
                "http_status": 0,
                "latency_ms": int((time.perf_counter() - t0) * 1000),
                "payload": {
                    "error": "research_desk_unavailable",
                    "retryable": True,
                    "detail": str(exc)[:240],
                },
                "error": str(exc),
                "timeout": "timeout" in str(exc).lower(),
                "raw_is_html": False,
                "transport": h.mode,
            }
        row = h.evaluate(
            {**case, "isolate_from_previous": isolate},
            transport,
            previous_entities=previous_entities if isolate else None,
        )
        row = _enrich_row(row, transport)
        questions.append(row)
        if isolate:
            previous_entities = list(row.get("entities") or [])

        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        orch = (payload.get("ask_orchestration") or {}) if isinstance(payload, dict) else {}
        _print_execution_trace(row, orch if isinstance(orch, dict) else {})
        flush(partial=True)
        print(
            f"[baseline] wrote partial → {primary.name} "
            f"pass={row.get('pass')} timeout={row.get('timeout')} "
            f"fallback={row.get('fallback_used')} "
            f"stage={row.get('last_completed_stage')} "
            f"ms={row.get('latency_ms')}",
            flush=True,
        )

    report = flush(partial=False)
    print_health_summary(report)

    # Stable alias ONLY if absent — never overwrite a prior pre_ikl pointer
    alias = out_dir / "ask_test_report_pre_ikl.json"
    if not alias.exists():
        _write_atomic(alias, report)
        print(f"[baseline] created pointer {alias}", flush=True)
    else:
        # Write a sidecar pointer to the latest stamped file without clobbering content
        pointer = out_dir / "ask_test_report_pre_ikl.latest"
        pointer.write_text(str(primary.name) + "\n", encoding="utf-8")
        print(
            f"[baseline] kept existing {alias.name}; latest → {primary.name}",
            flush=True,
        )

    print(
        f"[baseline] DONE pass_rate={report['pass_rate']:.0%} "
        f"avg_latency_ms={report['average_latency_ms']} "
        f"fallback_rate={report['comparison_metrics'].get('fallback_rate')} "
        f"artifact={primary}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("[baseline] interrupted — partial report should already be on disk", flush=True)
        raise SystemExit(130)
