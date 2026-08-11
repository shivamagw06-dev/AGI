#!/usr/bin/env python3
"""Railway entrypoint for a bounded Ask AGI improvement session."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agi_improvement_engine.worker import run_session  # noqa: E402
from agi_improvement_engine.schema import RAMP_STAGES  # noqa: E402


async def main() -> int:
    runtime_hours = min(6.0, max(0.1, float(os.environ.get("AGI_IMPROVEMENT_RUNTIME_HOURS", "6"))))
    total_limit = int(os.environ.get("AGI_IMPROVEMENT_QUESTION_LIMIT", "100"))
    batch_size = min(100, max(1, int(os.environ.get("AGI_IMPROVEMENT_BATCH_SIZE", "10"))))
    concurrency = int(os.environ.get("AGI_IMPROVEMENT_CONCURRENCY", "2"))
    endpoint = os.environ.get("AGI_ENGINE_URL", "").strip()
    output_dir = Path(os.environ.get("AGI_IMPROVEMENT_OUTPUT_DIR", "/data/agi-improvement"))
    if not endpoint:
        raise RuntimeError("AGI_ENGINE_URL is required")
    if total_limit not in RAMP_STAGES:
        raise RuntimeError(f"AGI_IMPROVEMENT_QUESTION_LIMIT must be a validated ramp stage: {RAMP_STAGES}")
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
    print(json.dumps({"completed": completed, "batches": len(reports), "reports": reports}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
