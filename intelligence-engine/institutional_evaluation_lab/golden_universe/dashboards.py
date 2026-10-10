"""Coverage + sector dashboards for golden-universe evaluation runs."""

from __future__ import annotations

from typing import Any


def _avg(vals: list[float]) -> float | None:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def coverage_dashboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    by_ev = {"Complete": 0, "Partial": 0, "Insufficient": 0}
    readiness: list[float] = []
    runtimes: list[float] = []
    gate_pass = 0
    gate_fail = 0
    live_price_n = 0
    qa_pass = 0

    for r in rows:
        ev = str(r.get("evidence_class") or "Insufficient")
        by_ev[ev] = by_ev.get(ev, 0) + 1
        if r.get("recommendation_readiness") is not None:
            try:
                readiness.append(float(r["recommendation_readiness"]))
            except (TypeError, ValueError):
                pass
        if r.get("runtime_ms") is not None:
            try:
                runtimes.append(float(r["runtime_ms"]))
            except (TypeError, ValueError):
                pass
        if r.get("gate") == "PASS":
            gate_pass += 1
        else:
            gate_fail += 1
        if r.get("live_price") or r.get("price_available"):
            live_price_n += 1
        if r.get("qa_passed"):
            qa_pass += 1

    denom = n or 1
    return {
        "companies": n,
        "evidence_coverage": by_ev,
        "average_readiness_pct": _avg(readiness),
        "average_runtime_ms": int(_avg(runtimes) or 0) if runtimes else None,
        "average_runtime_s": round((_avg(runtimes) or 0) / 1000.0, 2) if runtimes else None,
        "gate_pass_rate_pct": round(100.0 * gate_pass / denom, 1),
        "gate_fail_rate_pct": round(100.0 * gate_fail / denom, 1),
        "live_price_coverage_pct": round(100.0 * live_price_n / denom, 1),
        "qa_pass_rate_pct": round(100.0 * qa_pass / denom, 1),
        "gate_pass": gate_pass,
        "gate_fail": gate_fail,
    }


def sector_dashboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_sector: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sec = str(r.get("sector") or "Unknown")
        by_sector.setdefault(sec, []).append(r)

    table: list[dict[str, Any]] = []
    for sector, items in sorted(by_sector.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        cov = coverage_dashboard(items)
        table.append(
            {
                "sector": sector,
                "n": len(items),
                "avg_readiness_pct": cov["average_readiness_pct"],
                "avg_runtime_s": cov["average_runtime_s"],
                "gate_pass_pct": cov["gate_pass_rate_pct"],
                "evidence_complete": cov["evidence_coverage"].get("Complete", 0),
                "evidence_partial": cov["evidence_coverage"].get("Partial", 0),
                "evidence_insufficient": cov["evidence_coverage"].get("Insufficient", 0),
            }
        )
    return {"sectors": table, "sector_count": len(table)}


def bucket_dashboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        b = str(r.get("bucket") or "unknown")
        by_bucket.setdefault(b, []).append(r)
    table = []
    for bucket, items in by_bucket.items():
        cov = coverage_dashboard(items)
        table.append(
            {
                "bucket": bucket,
                "n": len(items),
                "avg_readiness_pct": cov["average_readiness_pct"],
                "gate_pass_pct": cov["gate_pass_rate_pct"],
                "avg_runtime_s": cov["average_runtime_s"],
            }
        )
    return {"buckets": table}
