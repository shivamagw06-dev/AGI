#!/usr/bin/env python3
"""Railway entrypoint for a bounded Ask AGI improvement session."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agi_improvement_engine.schema import RAMP_STAGES, SMOKE_TEST_COUNT  # noqa: E402
from agi_improvement_engine.worker import run_session  # noqa: E402


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_endpoint() -> str:
    endpoint = (
        os.environ.get("AGI_ENGINE_URL")
        or os.environ.get("INTELLIGENCE_ENGINE_URL")
        or ""
    ).strip().rstrip("/")
    if endpoint and not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    return endpoint


def _preflight(endpoint: str) -> None:
    health_url = f"{endpoint.rstrip('/')}/v1/health"
    timeout = float(os.environ.get("AGI_ENGINE_HEALTH_TIMEOUT_SEC", "15"))
    request = urllib.request.Request(health_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")[:500]
            print(f"[agi-improvement] engine health ok ({response.status}) {health_url}", flush=True)
            if body:
                print(f"[agi-improvement] health body: {body[:240]}", flush=True)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Engine health check failed ({exc.code}) for {health_url}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Engine health check failed for {health_url}: {exc}") from exc


async def main() -> int:
    dry_run = _truthy("AGI_IMPROVEMENT_DRY_RUN")
    smoke = _truthy("AGI_IMPROVEMENT_SMOKE_TEST")
    runtime_hours = min(6.0, max(0.1, float(os.environ.get("AGI_IMPROVEMENT_RUNTIME_HOURS", "6"))))
    total_limit = int(os.environ.get("AGI_IMPROVEMENT_QUESTION_LIMIT", "100"))
    if smoke:
        total_limit = SMOKE_TEST_COUNT
    batch_size = min(100, max(1, int(os.environ.get("AGI_IMPROVEMENT_BATCH_SIZE", "10"))))
    concurrency = max(1, min(int(os.environ.get("AGI_IMPROVEMENT_CONCURRENCY", "2")), 8))
    endpoint = _resolve_endpoint()
    output_dir = Path(os.environ.get("AGI_IMPROVEMENT_OUTPUT_DIR", "/data/agi-improvement"))

    if not endpoint and not dry_run:
        raise RuntimeError("AGI_ENGINE_URL or INTELLIGENCE_ENGINE_URL is required")
    if not dry_run and not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY is required for live evaluation")
    if not smoke and total_limit not in RAMP_STAGES:
        raise RuntimeError(f"AGI_IMPROVEMENT_QUESTION_LIMIT must be a validated ramp stage: {RAMP_STAGES}")

    print(
        "[agi-improvement] boot "
        + json.dumps({
            "dry_run": dry_run,
            "smoke_test": smoke,
            "endpoint": endpoint,
            "total_limit": total_limit,
            "batch_size": batch_size,
            "concurrency": concurrency,
            "output_dir": str(output_dir),
        }),
        flush=True,
    )

    if dry_run:
        report = await run_session(count=total_limit, endpoint=endpoint, execute=False, output_dir=output_dir)
        print(json.dumps(report, indent=2))
        return 0

    _preflight(endpoint)

    deadline = time.monotonic() + runtime_hours * 3600
    completed = 0
    reports = []
    while completed < total_limit and time.monotonic() < deadline:
        count = min(batch_size, total_limit - completed)
        report = await run_session(
            count=count, endpoint=endpoint, execute=True,
            concurrency=concurrency, output_dir=output_dir,
        )
        reports.append(report)
        completed += report["completed"]
        if report["completed"] == 0:
            await asyncio.sleep(30)
    summary = {"completed": completed, "batches": len(reports), "reports": reports}
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
