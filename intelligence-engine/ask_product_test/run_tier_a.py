#!/usr/bin/env python3
"""Run Tier A (SMOKE-01..08) only — founder gate before full 42-case suite.

Usage:
  cd intelligence-engine
  ASK_TEST_MODE=inprocess python3 -m ask_product_test.run_tier_a
  ASK_TEST_MODE=live ASK_TEST_BASE=https://... python3 -m ask_product_test.run_tier_a

Writes:
  artifacts/tier_a_fix_report.json
  artifacts/tier_a_fix_report_<UTC>.json  (stamped, never overwritten)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ask_product_test.harness import AskProductHarness, _artifacts_dir, print_health_summary
from ask_product_test.prompts import SMOKE_PROMPTS
from ask_product_test.run_baseline import _enrich_row, _print_execution_trace, _ts, _write_atomic


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _row_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    orch_lat = row.get("orchestration_latency") or {}
    funnel = row.get("funnel") or {}
    return {
        "id": row.get("id"),
        "prompt": row.get("prompt"),
        "pass": bool(row.get("pass")),
        "live_gate_pass": bool(row.get("live_gate_pass", row.get("pass"))),
        "completed": bool(row.get("completed")),
        "latency_ms": row.get("latency_ms"),
        "entity": row.get("entity"),
        "entity_confidence": row.get("entity_confidence"),
        "reasoning_ms": orch_lat.get("reasoning_ms") or row.get("reasoning_ms"),
        "assembly_ms": orch_lat.get("assembly_ms") or row.get("assembly_ms"),
        "retrieved": funnel.get("retrieved"),
        "ranked": funnel.get("ranked"),
        "passed": funnel.get("passed"),
        "referenced": funnel.get("referenced"),
        "fallback": bool(row.get("fallback_used") or row.get("fallback")),
        "timeout": bool(row.get("timeout")),
        "engine_reached": row.get("engine_reached"),
        "ask_trace_id": row.get("ask_trace_id"),
        "last_completed_stage": row.get("last_completed_stage"),
        "short_circuit": (row.get("degradation") or {}).get("short_circuit")
        if isinstance(row.get("degradation"), dict)
        else row.get("short_circuit"),
        "failures": row.get("failures") or [],
        "live_gate_failures": row.get("live_gate_failures") or [],
    }


def _apply_live_founder_gate(row: Dict[str, Any], case: Dict[str, Any], transport: Dict[str, Any]) -> Dict[str, Any]:
    """Founder live gate — Node desk fallback must NOT count as a Tier A pass."""
    payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
    orch = (payload.get("ask_orchestration") or {}) if isinstance(payload, dict) else {}
    deg = (payload.get("degradation") or {}) if isinstance(payload, dict) else {}
    funnel = row.get("funnel") or orch.get("funnel") or orch.get("evidence") or {}
    short = deg.get("short_circuit") or orch.get("short_circuit")
    reco = bool(case.get("recommendation_bait"))
    failures: List[str] = []

    if transport.get("raw_is_html") or int(transport.get("http_status") or 0) in {502, 503}:
        failures.append("html_or_gateway_5xx")
    if row.get("timeout") or orch.get("timeout"):
        failures.append("timeout")
    if row.get("fallback_used") or orch.get("fallback") or orch.get("fallback_used"):
        failures.append("gateway_fallback")
    if not row.get("ask_trace_id") and not orch.get("ask_trace_id"):
        failures.append("missing_ask_trace_id")
    engine_reached = orch.get("engine_reached")
    if engine_reached is False:
        failures.append("engine_not_reached")
    stage = row.get("last_completed_stage") or orch.get("last_completed_stage") or ""
    if reco:
        if short != "recommendation_policy":
            failures.append("recommendation_did_not_short_circuit")
    else:
        if stage in {"", "http_ingress"} and not orch.get("completed"):
            failures.append("stuck_at_http_ingress")
        retrieved = int(funnel.get("retrieved") or 0)
        if retrieved <= 0 and short != "recommendation_policy":
            failures.append("empty_evidence_funnel")

    row["short_circuit"] = short
    row["engine_reached"] = engine_reached
    row["live_gate_failures"] = failures
    # Contract pass AND live founder gate
    row["live_gate_pass"] = bool(row.get("pass")) and not failures
    if failures:
        row["pass"] = False
        row["failures"] = list(row.get("failures") or []) + [f"live_gate:{f}" for f in failures]
    return row


def _wait_engine_healthy(*, base_url: str, attempts: int = 40, sleep_s: float = 15.0) -> bool:
    """Best-effort preflight: engine /v1/ui/health via gateway or direct."""
    import urllib.error
    import urllib.request

    candidates = [
        os.environ.get("ASK_TEST_ENGINE_BASE", "").rstrip("/"),
        "https://agib-intelligence-engine.onrender.com",
    ]
    for i in range(1, attempts + 1):
        ok = False
        for root in candidates:
            if not root:
                continue
            url = f"{root}/v1/ui/health"
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                    if int(resp.status) == 200:
                        ok = True
                        break
            except Exception:
                continue
        # Also require gateway health
        try:
            gurl = f"{base_url.rstrip('/')}/api/health"
            with urllib.request.urlopen(gurl, timeout=15) as resp:  # noqa: S310
                gateway_ok = int(resp.status) == 200
        except Exception:
            gateway_ok = False
        print(f"[tier-a] preflight ({i}/{attempts}) engine_ok={ok} gateway_ok={gateway_ok}", flush=True)
        if ok and gateway_ok:
            return True
        time.sleep(sleep_s)
    return False


def _load_previous_baseline() -> Optional[Dict[str, Any]]:
    root = _artifacts_dir()
    # Prefer paused pre-IKL baseline from the aborted 42-case run
    candidates = [
        root / "ask_test_report_pre_ikl_20260801T064555Z_paused.json",
        root / "ask_test_report_pre_ikl_20260801T064555Z_preserved.json",
        root / "ask_test_report_pre_ikl_20260801T064555Z.json",
        root / "ask_test_report_pre_ikl.json",
    ]
    # Also check repo-root artifacts/
    for extra in (
        Path("/workspace/artifacts"),
        Path(__file__).resolve().parents[2] / "artifacts",
    ):
        if extra.is_dir():
            candidates.extend(
                [
                    extra / "ask_test_report_pre_ikl_20260801T064555Z_paused.json",
                    extra / "ask_test_report_pre_ikl_20260801T064555Z_preserved.json",
                    extra / "ask_test_report_pre_ikl_20260801T064555Z.json",
                ]
            )
    for path in candidates:
        try:
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def _compare(tier_rows: List[Dict[str, Any]], previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    prev_by_id: Dict[str, Any] = {}
    if isinstance(previous, dict):
        for q in previous.get("questions") or []:
            if isinstance(q, dict) and str(q.get("id") or "").startswith("SMOKE-"):
                prev_by_id[str(q["id"])] = q
    deltas = []
    for row in tier_rows:
        pid = str(row.get("id") or "")
        prev = prev_by_id.get(pid) or {}
        deltas.append(
            {
                "id": pid,
                "prev_pass": prev.get("pass"),
                "now_pass": row.get("pass"),
                "prev_latency_ms": prev.get("latency_ms"),
                "now_latency_ms": row.get("latency_ms"),
                "prev_timeout": prev.get("timeout"),
                "now_timeout": row.get("timeout"),
                "prev_fallback": prev.get("fallback_used") or prev.get("fallback"),
                "now_fallback": row.get("fallback"),
                "prev_reasoning_ms": (prev.get("orchestration_latency") or {}).get("reasoning_ms"),
                "now_reasoning_ms": row.get("reasoning_ms"),
            }
        )
    tier_pass = sum(1 for r in tier_rows if r.get("pass"))
    return {
        "previous_artifact_note": "compared against paused/preserved pre-IKL baseline when available",
        "tier_a_passed": tier_pass,
        "tier_a_total": len(tier_rows),
        "tier_a_gate": "PASS" if tier_pass == 8 else "FAIL",
        "deltas": deltas,
        "recommend_full_suite": tier_pass == 8,
        "recommend_ikl_merge": False,  # never until Tier A green + post-IKL baseline
    }


def main() -> int:
    latency = int(
        os.environ.get("ASK_TEST_LATENCY_MS")
        or os.environ.get("ASK_ENGINE_TIMEOUT_MS")
        or "120000"
    )
    # Default inprocess so local fixes are verified before deploy.
    os.environ.setdefault("ASK_TEST_MODE", "inprocess")
    h = AskProductHarness(latency_budget_ms=latency)
    stamp = _stamp()
    out_dir = _artifacts_dir()
    stamped = out_dir / f"tier_a_fix_report_{stamp}.json"
    stable = out_dir / "tier_a_fix_report.json"
    # Also write under /workspace/artifacts when that is the repo root artifacts dir
    workspace_arts = Path("/workspace/artifacts")

    cases = list(SMOKE_PROMPTS)
    cooldown_s = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "8") or "8")
    print(
        f"[tier-a] mode={h.mode} base={h.base_url} "
        f"latency_budget_ms={latency} cases={len(cases)} cooldown_s={cooldown_s}",
        flush=True,
    )

    if h.mode == "live":
        if not _wait_engine_healthy(base_url=h.base_url):
            print("[tier-a] ENGINE_NOT_HEALTHY — aborting before false-green fallbacks", flush=True)
            report = {
                "suite": "Tier A founder acceptance (SMOKE-01..08)",
                "timestamp": _ts(),
                "mode": h.mode,
                "base_url": h.base_url,
                "tier_a_gate": "FAIL",
                "passed": 0,
                "total": 0,
                "note": "Aborted: intelligence engine unhealthy before Tier A start",
                "recommend_full_suite": False,
            }
            _write_atomic(stamped, report)
            _write_atomic(stable, report)
            return 2

    questions: List[Dict[str, Any]] = []
    for idx, case in enumerate(cases, 1):
        if idx > 1 and cooldown_s > 0:
            # Give Render Starter headroom between heavy Asks (avoids 502 cascade).
            time.sleep(cooldown_s)
            if h.mode == "live":
                _wait_engine_healthy(base_url=h.base_url, attempts=8, sleep_s=5.0)
        print(
            f"\n[tier-a] ({idx}/{len(cases)}) {case.get('id')} — {case.get('prompt')[:100]}",
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
        row = h.evaluate(case, transport, previous_entities=None)
        row = _enrich_row(row, transport)
        # Attach degradation for short_circuit reporting
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        if isinstance(payload, dict):
            row["degradation"] = payload.get("degradation") or {}
        if h.mode == "live":
            row = _apply_live_founder_gate(row, case, transport)
        else:
            row["live_gate_pass"] = bool(row.get("pass"))
        questions.append(row)
        orch = (payload.get("ask_orchestration") or {}) if isinstance(payload, dict) else {}
        _print_execution_trace(row, orch if isinstance(orch, dict) else {})
        print(
            f"[tier-a] pass={row.get('pass')} live_gate={row.get('live_gate_pass')} "
            f"timeout={row.get('timeout')} fallback={row.get('fallback_used')} "
            f"ms={row.get('latency_ms')} gate_failures={row.get('live_gate_failures')}",
            flush=True,
        )

    summaries = [_row_summary(q) for q in questions]
    previous = _load_previous_baseline()
    comparison = _compare(summaries, previous)
    passed = sum(1 for s in summaries if s.get("live_gate_pass" if h.mode == "live" else "pass"))
    gate_ok = passed == 8
    comparison["recommend_full_suite"] = gate_ok
    comparison["false_green_guard"] = (
        "live mode rejects gateway_fallback / empty funnel / missing short-circuit"
        if h.mode == "live"
        else "inprocess contract gate"
    )
    report = {
        "suite": "Tier A founder acceptance (SMOKE-01..08)",
        "timestamp": _ts(),
        "mode": h.mode,
        "base_url": h.base_url,
        "latency_budget_ms": latency,
        "partial": False,
        "completed": True,
        "pass_rate": (passed / len(summaries)) if summaries else 0.0,
        "passed": passed,
        "total": len(summaries),
        "tier_a_gate": "PASS" if gate_ok else "FAIL",
        "questions": summaries,
        "full_questions": questions,
        "comparison": comparison,
        "artifact": str(stable),
        "stamped_artifact": str(stamped),
        "note": (
            "Tier A only — do not run full 42-case suite until live gate 8/8 "
            "(no fallback, no timeout, funnel/stage/trace present). "
            "Do not treat IKL A/B as valid until then."
        ),
    }
    _write_atomic(stamped, report)
    _write_atomic(stable, report)
    if workspace_arts.is_dir():
        _write_atomic(workspace_arts / "tier_a_fix_report.json", report)
        _write_atomic(workspace_arts / stamped.name, report)
    try:
        opt = Path("/opt/cursor/artifacts")
        if opt.is_dir():
            _write_atomic(opt / "tier_a_fix_report.json", report)
            _write_atomic(opt / stamped.name, report)
    except Exception:
        pass

    print_health_summary(
        {
            "pass_rate": report["pass_rate"],
            "passed": passed,
            "total": len(summaries),
            "average_latency_ms": int(
                sum(s.get("latency_ms") or 0 for s in summaries) / max(1, len(summaries))
            ),
            "questions": questions,
            "comparison_metrics": {
                "fallback_rate": sum(1 for s in summaries if s.get("fallback")) / max(1, len(summaries)),
            },
        }
    )
    print(
        f"[tier-a] GATE={report['tier_a_gate']} {passed}/8 "
        f"recommend_full_suite={comparison['recommend_full_suite']} "
        f"artifact={stable}",
        flush=True,
    )
    return 0 if passed == 8 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("[tier-a] interrupted", flush=True)
        raise SystemExit(130)
