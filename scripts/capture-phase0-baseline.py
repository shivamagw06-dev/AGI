#!/usr/bin/env python3
"""Capture a redacted, reproducible AGI production operations baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = "https://agib-intelligence-engine.onrender.com/v1"
ENDPOINTS = {
    "engine": "/health",
    "market_data": "/market-data/health",
    "features": "/features/health",
    "warehouse": "/warehouse/health",
    "warehouse_backfill": "/warehouse/backfill/status",
    "knowledge_memory": "/kip/health",
    "continuous_gather": "/continuous-gather-learn/health",
    "ask_pipeline": "/ask/pipeline",
    "forecast": "/fie/health",
    "forecast_runtime": "/fie/runtime/status",
    "dossiers": "/company-dossier/health",
    "validation": "/validation/health",
    "continuous_evaluation": "/cre/health",
    "macro_regime": "/e01/health",
    "factor_style": "/e02/health",
    "cross_sectional_alpha": "/e03/health",
    "relative_value": "/e04/health",
    "events": "/e05/health",
    "volatility": "/e08/health",
    "trend": "/e09/health",
    "portfolio_construction": "/e10/health",
    "sentiment": "/e11/health",
    "fundamental_ls": "/e13/health",
    "risk_overlay": "/e14/health",
    "composite_shadow": "/l4/health",
}
SENSITIVE = ("token", "secret", "password", "authorization", "api_key", "apikey")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(term in key.lower() for term in SENSITIVE) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def fetch(path: str, timeout: float) -> dict[str, Any]:
    url = f"{ENGINE}{path}"
    started = datetime.now(timezone.utc)
    result = subprocess.run(
        [
            "curl", "--silent", "--show-error", "--max-time", str(timeout),
            "--header", "Accept: application/json", "--write-out",
            "\n%{http_code}\n%{time_total}", url,
        ],
        capture_output=True,
        text=True,
    )
    try:
        body, status, elapsed = result.stdout.rsplit("\n", 2)
        payload = json.loads(body)
        http_status = int(status)
        if result.returncode != 0 or not 200 <= http_status < 300:
            raise ValueError(result.stderr.strip() or f"HTTP {http_status}")
        return {
            "ok": True,
            "http_status": http_status,
            "latency_ms": round(float(elapsed) * 1000, 2),
            "url": url,
            "payload": redact(payload),
        }
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "http_status": None,
            "latency_ms": round(
                (datetime.now(timezone.utc) - started).total_seconds() * 1000, 2
            ),
            "url": url,
            "error": (str(exc) or result.stderr.strip())[:300],
        }


def summarize(probes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def payload(name: str) -> dict[str, Any]:
        return probes.get(name, {}).get("payload") or {}

    warehouse = payload("warehouse")
    kip = payload("knowledge_memory")
    gather = payload("continuous_gather")
    forecast_runtime = payload("forecast_runtime").get("pipeline") or {}
    engine_rows: dict[str, int] = {}
    for name in (
        "macro_regime", "factor_style", "cross_sectional_alpha", "relative_value",
        "events", "volatility", "trend", "portfolio_construction", "sentiment",
        "fundamental_ls", "risk_overlay", "composite_shadow",
    ):
        metrics = payload(name).get("metrics") or {}
        engine_rows[name] = int(metrics.get("runs") or 0)

    return {
        "warehouse": {
            "status": warehouse.get("status"),
            "total_rows": warehouse.get("total_rows"),
            "tabs": warehouse.get("tabs"),
            "populated_tabs": len(warehouse.get("populated_tabs") or []),
            "row_counts": warehouse.get("row_counts") or {},
        },
        "knowledge_memory": kip.get("stats") or {},
        "continuous_gather": {
            "status": gather.get("status"),
            "effective_gather": gather.get("effective_gather"),
            "sidecar_fresh": (gather.get("gather_sidecar") or {}).get("fresh"),
            "sidecar_age_sec": (gather.get("gather_sidecar") or {}).get("age_sec"),
            "heartbeat": (gather.get("gather_sidecar") or {}).get("beat_at"),
        },
        "forecast_coverage": forecast_runtime,
        "engine_run_counts": engine_rows,
        "probe_failures": [name for name, result in probes.items() if not result.get("ok")],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    probes: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as pool:
        futures = {
            pool.submit(fetch, path, args.timeout): name for name, path in ENDPOINTS.items()
        }
        for future in as_completed(futures):
            probes[futures[future]] = future.result()
    document = {
        "schema_version": "agi-phase0-baseline-v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "repository": "shivamagw06-dev/AGI",
            "branch": git("branch", "--show-current"),
            "commit": git("rev-parse", "HEAD"),
            "commit_subject": git("log", "-1", "--pretty=%s"),
            "engine_base_url": ENGINE,
        },
        "freeze": {
            "new_engines": False,
            "new_strategy_families": False,
            "new_product_pages": False,
            "allowed_changes": [
                "reliability", "data_quality", "coverage", "observability",
                "validation", "security", "performance", "bug_fixes",
            ],
        },
        "summary": summarize(probes),
        "probes": probes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.output}")
    return 0 if not document["summary"]["probe_failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
