"""Rolling source reliability scores for Mission Control trends."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from institutional_data.persistence.checkpoint import CheckpointManager

REPORT = "source_reliability_rolling"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_connector_sample(
    source_id: str,
    *,
    ok: bool,
    latency_ms: float | int | None = None,
    coverage_pct: float | None = None,
    parser_path: str | None = None,
) -> None:
    ck = CheckpointManager()
    day = datetime.now(timezone.utc).date().isoformat()
    path = ck.path_for(REPORT)
    from institutional_data.persistence.atomic import atomic_write_json, file_lock

    with file_lock(path):
        data = ck.load(REPORT) or {"days": {}, "sources": {}}
        days = data.setdefault("days", {})
        day_row = days.setdefault(day, {})
        src = day_row.setdefault(source_id, {"ok": 0, "fail": 0, "latency_ms": [], "coverage": [], "parsers": {}})
        if ok:
            src["ok"] = int(src.get("ok") or 0) + 1
        else:
            src["fail"] = int(src.get("fail") or 0) + 1
        if latency_ms is not None:
            lat = list(src.get("latency_ms") or [])
            lat.append(float(latency_ms))
            src["latency_ms"] = lat[-200:]
        if coverage_pct is not None:
            cov = list(src.get("coverage") or [])
            cov.append(float(coverage_pct))
            src["coverage"] = cov[-200:]
        if parser_path:
            parsers = dict(src.get("parsers") or {})
            parsers[parser_path] = int(parsers.get(parser_path) or 0) + 1
            src["parsers"] = parsers
        # Trim days to ~60
        for k in sorted(days.keys())[:-60]:
            days.pop(k, None)
        data["updated_at"] = _now()
        atomic_write_json(path, data)
        try:
            from knowledge_factory.historical_depth import store as hd_store

            hd_store.put_report(REPORT, data)
        except Exception:
            pass


def reliability_dashboard() -> list[dict[str, Any]]:
    ck = CheckpointManager()
    data = ck.load(REPORT) or {}
    days = data.get("days") or {}
    # Aggregate last 7 days
    keys = sorted(days.keys())[-7:]
    agg: dict[str, dict[str, Any]] = {}
    for day in keys:
        for src, row in (days.get(day) or {}).items():
            a = agg.setdefault(src, {"ok": 0, "fail": 0, "latency_ms": [], "coverage": [], "parsers": {}})
            a["ok"] += int(row.get("ok") or 0)
            a["fail"] += int(row.get("fail") or 0)
            a["latency_ms"].extend(list(row.get("latency_ms") or []))
            a["coverage"].extend(list(row.get("coverage") or []))
            for p, n in (row.get("parsers") or {}).items():
                a["parsers"][p] = int(a["parsers"].get(p) or 0) + int(n)

    out = []
    for src, a in sorted(agg.items()):
        n = a["ok"] + a["fail"]
        lat = a["latency_ms"]
        cov = a["coverage"]
        out.append(
            {
                "source": src,
                "availability_pct": round(100.0 * a["ok"] / n, 1) if n else None,
                "failure_pct": round(100.0 * a["fail"] / n, 1) if n else None,
                "latency_ms_avg": round(sum(lat) / len(lat), 1) if lat else None,
                "coverage_pct_avg": round(sum(cov) / len(cov), 1) if cov else None,
                "parser_stability": max(a["parsers"].values()) / sum(a["parsers"].values()) if a["parsers"] else None,
                "samples_7d": n,
                "freshness": keys[-1] if keys else None,
            }
        )
    return out
