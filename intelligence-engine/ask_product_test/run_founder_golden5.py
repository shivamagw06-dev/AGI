#!/usr/bin/env python3
"""Founder Acceptance — Golden 5 (live Ask, user/CIO lens).

Does not score like a regression harness. Captures full answers for
manual founder scoring (answered / evidence / grounding / reasoning /
no hallucination / readability).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE = (
    __import__("os").environ.get("ASK_TEST_BASE")
    or "https://finance-news-backend-19i5.onrender.com"
).rstrip("/")
COOLDOWN_S = float(__import__("os").environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "12") or "12")
TIMEOUT_S = float(__import__("os").environ.get("ASK_TEST_LATENCY_MS", "120000") or "120000") / 1000.0

CASES: List[Dict[str, str]] = [
    {"id": "G1", "prompt": "What is Reliance Industries' business model?"},
    {"id": "G2", "prompt": "Compare Infosys vs TCS."},
    {
        "id": "G3",
        "prompt": "What did Meta say in Q2 2026 about AI infrastructure spending?",
    },
    {"id": "G4", "prompt": "Should I buy HDFC Bank tomorrow?"},
    {"id": "G5", "prompt": "Explain XYZ Quantum Robotics Pvt Ltd."},
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _artifacts() -> Path:
    env = (__import__("os").environ.get("ASK_TEST_ARTIFACTS") or "").strip()
    if env:
        return Path(env)
    opt = Path("/opt/cursor/artifacts")
    if opt.is_dir():
        return opt
    return Path("/workspace/artifacts")


def ask(question: str) -> Dict[str, Any]:
    body = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/ui/search",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = int(resp.status)
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        status = int(exc.code)
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"raw": raw[:2000]}
        return {
            "http_status": status,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "payload": payload,
            "request_id": headers.get("x-request-id") or headers.get("x-ask-trace-id"),
            "error": f"HTTPError {status}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "http_status": 0,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "payload": {},
            "request_id": None,
            "error": str(exc)[:400],
        }
    try:
        payload = json.loads(raw) if raw else {}
    except Exception:
        payload = {"raw": raw[:2000]}
    return {
        "http_status": status,
        "latency_ms": int((time.perf_counter() - t0) * 1000),
        "payload": payload,
        "request_id": headers.get("x-request-id") or headers.get("x-ask-trace-id"),
        "error": None,
    }


def extract_row(case: Dict[str, str], tr: Dict[str, Any]) -> Dict[str, Any]:
    p = tr.get("payload") if isinstance(tr.get("payload"), dict) else {}
    ans = p.get("answer") if isinstance(p.get("answer"), dict) else {}
    summary = (
        ans.get("summary")
        or ans.get("executive_summary")
        or p.get("summary")
        or ""
    )
    if not summary and isinstance(p.get("answer"), str):
        summary = p["answer"]
    why = ans.get("why") or ans.get("bullets") or p.get("why") or []
    orch = p.get("ask_orchestration") or {}
    if not orch and isinstance(p.get("degradation"), dict):
        orch = p["degradation"].get("ask_orchestration") or {}
    evidence = p.get("evidence") or ans.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []
    supporting = p.get("supporting_research") or ans.get("supporting_research") or []
    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "http_status": tr.get("http_status"),
        "latency_ms": tr.get("latency_ms"),
        "request_id": tr.get("request_id")
        or orch.get("request_id")
        or orch.get("ask_trace_id"),
        "fallback_used": bool(
            orch.get("fallback_used") or orch.get("fallback")
        ),
        "fallback_reason": orch.get("fallback_reason") or orch.get("reason"),
        "engine_reached": orch.get("engine_reached"),
        "entity": orch.get("entity") or {},
        "funnel": orch.get("funnel") or orch.get("evidence"),
        "stance": ans.get("stance") or p.get("stance"),
        "house_view_label": ans.get("house_view_label") or p.get("house_view_label"),
        "summary": (summary if isinstance(summary, str) else str(summary))[:8000],
        "why": why[:16] if isinstance(why, list) else why,
        "evidence_count": len(evidence),
        "supporting_count": len(supporting) if isinstance(supporting, list) else 0,
        "evidence_sample": [
            {
                "title": e.get("title") if isinstance(e, dict) else None,
                "source": e.get("source") if isinstance(e, dict) else None,
                "id": e.get("id") if isinstance(e, dict) else None,
            }
            for e in evidence[:10]
        ],
        "detail": p.get("detail"),
        "status": p.get("status"),
        "policy": ans.get("policy") or p.get("policy"),
        "error": tr.get("error"),
        "orchestration_latency": orch.get("latency"),
        "last_completed_stage": orch.get("last_completed_stage"),
    }


def main() -> int:
    out_dir = _artifacts()
    out_dir.mkdir(parents=True, exist_ok=True)
    ws = Path("/workspace/artifacts")
    ws.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()

    print(f"[golden5] base={BASE} cooldown={COOLDOWN_S}s timeout={TIMEOUT_S}s", flush=True)
    try:
        urllib.request.urlopen(f"{BASE}/api/ui/health", timeout=20).read()
        print("[golden5] health ok", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[golden5] health wake: {exc}", flush=True)

    rows: List[Dict[str, Any]] = []
    for i, case in enumerate(CASES, 1):
        if i > 1 and COOLDOWN_S > 0:
            time.sleep(COOLDOWN_S)
        print(f"\n===== ({i}/5) {case['id']} =====\nQ: {case['prompt']}", flush=True)
        tr = ask(case["prompt"])
        row = extract_row(case, tr)
        rows.append(row)
        print(
            f"rid={row.get('request_id')} ms={row.get('latency_ms')} "
            f"fb={row.get('fallback_used')} status={row.get('http_status')} "
            f"engine={row.get('engine_reached')}",
            flush=True,
        )
        print("--- SUMMARY ---", flush=True)
        print((row.get("summary") or "")[:3000], flush=True)
        print("--- WHY ---", flush=True)
        for w in (row.get("why") or [])[:10]:
            print("-", str(w)[:400], flush=True)

    report = {
        "suite": "AGI Founder Acceptance — Golden 5",
        "version": "v1.0",
        "timestamp": _ts(),
        "base_url": BASE,
        "questions": rows,
        "note": "Manual founder scoring required — see capacity/acceptance rubric (max 30).",
    }
    path = out_dir / f"founder_acceptance_golden5_{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ws / path.name).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ws / "founder_acceptance_golden5_latest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n[golden5] WROTE {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
