"""Benchmark suite — accuracy / latency / coverage across filing classes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from financial_statements_engine.parsing.quality.certification import FIXTURES, certify_parser
from financial_statements_engine.util import now_iso

BENCHMARK_CLASSES = (
    "nse_xbrl",
    "bse_filings",
    "annual_reports",
    "quarterly_reports",
    "complex_tables",
    "segment_reporting",
    "restated_statements",
    "large_financial_institutions",
    "manufacturing",
    "it",
    "banks",
    "nbfcs",
    "insurance",
)


def run_benchmarks() -> dict[str, Any]:
    """v1: run certification fixture as NSE XBRL / IT proxy; expand fixtures over time."""
    from financial_statements_engine.parsing.production import parse_bytes

    t0 = time.perf_counter()
    cert = certify_parser()
    latency_ms = (time.perf_counter() - t0) * 1000.0

    fixture = json.loads((FIXTURES / "tcs_annual_min.json").read_text(encoding="utf-8"))
    data = json.dumps(fixture.get("document") or fixture, sort_keys=True).encode("utf-8")
    t1 = time.perf_counter()
    parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="bench:tcs",
    )
    parse_latency = (time.perf_counter() - t1) * 1000.0

    gm = cert.get("gate_metrics") or {}
    rows = [
        {
            "benchmark_class": "nse_xbrl",
            "sector_proxy": "it",
            "accuracy_pct": gm.get("canonical_mapping_accuracy_pct"),
            "precision": cert.get("precision"),
            "recall": cert.get("recall"),
            "latency_ms": round(parse_latency, 3),
            "coverage_pct": gm.get("metric_extraction_accuracy_pct"),
            "failure_rate_pct": 0.0 if cert.get("ok") else 100.0,
            "unknown_metrics_pct": gm.get("unknown_metric_rate_pct"),
            "passed": bool(cert.get("ok")),
        }
    ]
    # Placeholder rows for remaining classes (not yet instrumented)
    for cls in BENCHMARK_CLASSES:
        if cls in ("nse_xbrl", "it"):
            continue
        rows.append(
            {
                "benchmark_class": cls,
                "status": "pending_fixture",
                "passed": None,
            }
        )

    instrumented = [r for r in rows if r.get("passed") is not None]
    pass_rate = 100.0 * sum(1 for r in instrumented if r.get("passed")) / max(1, len(instrumented))

    return {
        "ok": pass_rate >= 100.0 and bool(cert.get("production_eligible")),
        "benchmark_classes": list(BENCHMARK_CLASSES),
        "rows": rows,
        "pass_rate_pct": pass_rate,
        "certification": cert,
        "suite_latency_ms": round(latency_ms, 3),
        "as_of": now_iso(),
        "issues_recommendations": False,
        "layer": "benchmark_suite",
    }
