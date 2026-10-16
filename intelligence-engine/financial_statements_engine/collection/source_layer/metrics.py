"""Per-source download metrics for Mission Control (FSE-02.3)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def _path() -> Path:
    root = ensure_dirs()
    path = root / "collection" / "source_metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_source_attempt(row: dict[str, Any]) -> None:
    entry = {"ts": now_iso(), **row}
    with _path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, default=str) + "\n")


def source_stats(*, limit: int = 5000) -> dict[str, dict[str, Any]]:
    path = _path()
    by: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return by
    lines = path.read_text(encoding="utf-8").splitlines()[-max(1, int(limit)) :]
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = str(row.get("source_id") or row.get("source") or "unknown")
        bucket = by.setdefault(
            sid,
            {"attempts": 0, "successes": 0, "failures": 0, "fallbacks": 0, "latencies_ms": [], "companies": set(), "filing_types": Counter(), "years": Counter()},
        )
        bucket["attempts"] += 1
        if row.get("ok"):
            bucket["successes"] += 1
        else:
            bucket["failures"] += 1
        if row.get("fallback"):
            bucket["fallbacks"] += 1
        if isinstance(row.get("latency_ms"), (int, float)):
            bucket["latencies_ms"].append(float(row["latency_ms"]))
        if row.get("ticker"):
            bucket["companies"].add(str(row["ticker"]).upper())
        if row.get("filing_type"):
            bucket["filing_types"][str(row["filing_type"])] += 1
        pe = str(row.get("period_end") or "")
        if len(pe) >= 4 and pe[:4].isdigit():
            bucket["years"][pe[:4]] += 1

    out: dict[str, dict[str, Any]] = {}
    for sid, b in by.items():
        lat = b["latencies_ms"]
        attempts = b["attempts"] or 1
        out[sid] = {
            "attempts": b["attempts"],
            "successes": b["successes"],
            "failures": b["failures"],
            "fallbacks": b["fallbacks"],
            "success_rate_pct": round(100.0 * b["successes"] / attempts, 2),
            "average_download_time_ms": round(sum(lat) / len(lat), 2) if lat else None,
            "companies": sorted(b["companies"]),
            "filing_types": dict(b["filing_types"]),
            "years": dict(b["years"]),
        }
    return out


def coverage_summary(*, limit: int = 5000) -> dict[str, Any]:
    stats = source_stats(limit=limit)
    by_source = {sid: {"success_rate_pct": v["success_rate_pct"], "attempts": v["attempts"], "companies_n": len(v["companies"])} for sid, v in stats.items()}
    by_company: Counter[str] = Counter()
    by_filing: Counter[str] = Counter()
    by_year: Counter[str] = Counter()
    failures = 0
    fallbacks = 0
    latencies: list[float] = []
    for v in stats.values():
        for c in v["companies"]:
            by_company[c] += 1
        for ft, n in (v.get("filing_types") or {}).items():
            by_filing[ft] += n
        for y, n in (v.get("years") or {}).items():
            by_year[y] += n
        failures += int(v.get("failures") or 0)
        fallbacks += int(v.get("fallbacks") or 0)
        if v.get("average_download_time_ms") is not None:
            latencies.append(float(v["average_download_time_ms"]))
    return {
        "coverage_by_source": by_source,
        "coverage_by_company": dict(by_company.most_common()),
        "coverage_by_filing_type": dict(by_filing.most_common()),
        "coverage_by_reporting_year": dict(sorted(by_year.items())),
        "failures": failures,
        "fallback_usage": fallbacks,
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "source_stats": {k: {kk: vv for kk, vv in v.items() if kk != "companies"} for k, v in stats.items()},
        "as_of": now_iso(),
    }
