"""API-facing surface for HVIE Universe Completion Programme."""

from __future__ import annotations

from typing import Any, Optional

from historical_valuation_intelligence.universe_programme import runtime
from historical_valuation_intelligence.universe_programme.models import (
    PROGRAMME_CODE,
    PROGRAMME_VERSION,
)


def health() -> dict[str, Any]:
    st = runtime.status()
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "role": "hvie_universe_completion",
        "vendor_historical_ratios": False,
        "reconstruction": "prices + statements + corporate actions + VPAE",
        "runtime": st.get("runtime"),
        "pipeline": st.get("pipeline"),
        "completion": st.get("completion"),
        "endpoints": [
            "/v1/hvie/runtime/board",
            "/v1/hvie/runtime/status",
            "/v1/hvie/runtime/company/{symbol}",
            "/v1/hvie/runtime/coverage",
            "/v1/hvie/runtime/pipeline",
            "/v1/hvie/runtime/sector",
            "/v1/hvie/runtime/industry",
            "/v1/hvie/runtime/market",
            "/v1/hvie/runtime/failures",
            "/v1/hvie/runtime/retry",
            "/v1/hvie/runtime/start",
            "/v1/hvie/runtime/stop",
            "/v1/hvie/runtime/resume",
            "/v1/hvie/runtime/retry/{symbol}",
            "/v1/hvie/runtime/reconstruct/{symbol}",
        ],
    }


def status() -> dict[str, Any]:
    return runtime.status()


def board() -> dict[str, Any]:
    return runtime.board()


def coverage() -> dict[str, Any]:
    st = runtime.status()
    pipe = st.get("pipeline") or {}
    universe = int(pipe.get("universe") or 0) or 1
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "universe": pipe.get("universe"),
        "eligible_pct": round(100.0 * int(pipe.get("eligible") or 0) / universe, 1),
        "complete_pct": round(100.0 * int(pipe.get("complete") or 0) / universe, 1),
        "percentile_pct": round(100.0 * int(pipe.get("percentiles") or 0) / universe, 1),
        "bands_pct": round(100.0 * int(pipe.get("bands") or 0) / universe, 1),
        "regime_pct": round(100.0 * int(pipe.get("regimes") or 0) / universe, 1),
        "research_pct": round(100.0 * int(pipe.get("research") or 0) / universe, 1),
        "pipeline": pipe,
        "throughput": st.get("throughput"),
    }


def pipeline_view() -> dict[str, Any]:
    return runtime.pipeline_dashboard()


def company(symbol: str) -> dict[str, Any]:
    return runtime.company_status(symbol)


def failures(limit: int = 100) -> dict[str, Any]:
    return runtime.failures(limit=limit)


def retry_queue(limit: int = 100) -> dict[str, Any]:
    from historical_valuation_intelligence.universe_programme import queue as q

    rows = [r for r in q.all_queue_rows() if str(r.get("queue_status") or "").upper() == "RETRY"]
    rows.sort(key=lambda r: str(r.get("next_retry_at") or ""))
    return {"ok": True, "count": len(rows), "rows": rows[: max(1, min(int(limit), 500))]}


def sector_view() -> dict[str, Any]:
    from historical_valuation_intelligence.universe_programme import queue as q
    from collections import defaultdict

    by: dict[str, dict[str, int]] = defaultdict(lambda: {
        "companies": 0, "complete": 0, "percentiles": 0, "observations": 0,
    })
    for r in q.all_queue_rows():
        sec = str(r.get("sector") or "Unknown")
        by[sec]["companies"] += 1
        by[sec]["observations"] += int(r.get("observations") or 0)
        if r.get("has_percentile"):
            by[sec]["percentiles"] += 1
        if str(r.get("lifecycle") or "").upper() == "COMPLETE":
            by[sec]["complete"] += 1
    rows = []
    for sec, c in sorted(by.items(), key=lambda kv: -kv[1]["companies"]):
        n = max(c["companies"], 1)
        rows.append({
            "sector": sec,
            "companies": c["companies"],
            "complete": c["complete"],
            "percentiles": c["percentiles"],
            "observations": c["observations"],
            "coverage_pct": round(100.0 * c["complete"] / n, 1),
        })
    return {"ok": True, "rows": rows, "programme": PROGRAMME_CODE}


def industry_view() -> dict[str, Any]:
    from historical_valuation_intelligence.universe_programme import queue as q
    from collections import defaultdict

    by: dict[str, dict[str, int]] = defaultdict(lambda: {
        "companies": 0, "complete": 0, "percentiles": 0,
    })
    for r in q.all_queue_rows():
        ind = str(r.get("industry") or "Unknown")
        by[ind]["companies"] += 1
        if r.get("has_percentile"):
            by[ind]["percentiles"] += 1
        if str(r.get("lifecycle") or "").upper() == "COMPLETE":
            by[ind]["complete"] += 1
    rows = []
    for ind, c in sorted(by.items(), key=lambda kv: -kv[1]["companies"])[:200]:
        n = max(c["companies"], 1)
        rows.append({
            "industry": ind,
            "companies": c["companies"],
            "complete": c["complete"],
            "percentiles": c["percentiles"],
            "coverage_pct": round(100.0 * c["complete"] / n, 1),
        })
    return {"ok": True, "rows": rows, "programme": PROGRAMME_CODE}


def market_view() -> dict[str, Any]:
    cov = coverage()
    try:
        from institutional_warehouse import store

        rows = store.fetch(
            "historical_market_medians",
            filters={"market": "ALL", "metric": "pe"},
            sort="as_of",
            order="desc",
            limit=5,
        ).get("rows") or []
    except Exception:
        rows = []
    latest = rows[0] if rows else {}
    return {
        "ok": True,
        "market_median_pe": latest.get("median_value"),
        "as_of": latest.get("as_of"),
        "company_count": latest.get("company_count"),
        "coverage": cov,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def start() -> dict[str, Any]:
    return runtime.start()


def stop() -> dict[str, Any]:
    return runtime.stop()


def resume() -> dict[str, Any]:
    return runtime.resume()


def run_batch(batch: int = 15) -> dict[str, Any]:
    return runtime.process_batch(batch=batch)


def retry_symbol(symbol: str) -> dict[str, Any]:
    return runtime.retry_symbol(symbol)


def reconstruct_symbol(symbol: str) -> dict[str, Any]:
    return runtime.reconstruct_symbol(symbol)


def persist_aggregates(metric: str = "pe") -> dict[str, Any]:
    return runtime.persist_aggregates(metric=metric)
