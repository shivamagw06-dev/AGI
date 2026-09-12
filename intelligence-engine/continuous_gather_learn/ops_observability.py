"""Operational observability for Continuous Gather → Learn.

Collector health, coverage heat map, source reliability, index coverage,
backfill throughput — Mission Control facing. Not a new architecture layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

OPS_VERSION = "cgl-ops-observability-v1.0.0"

# Display names for LIDI collectors
COLLECTOR_DISPLAY = (
    ("lidi_nse_bhavcopy_v1", "nse_bhavcopy", "NSE Bhavcopy", "NSE"),
    ("lidi_nse_announcements_v1", "nse_announcements", "NSE Announcements", "NSE"),
    ("lidi_bse_corporate_actions_v1", "bse_corporate_actions", "BSE Actions", "BSE"),
    ("lidi_rbi_dbie_v1", "rbi_dbie", "RBI", "RBI"),
    ("lidi_company_ir_v1", "company_ir", "Company IR", "Company IR"),
)

SOURCE_KEYS = ("Yahoo", "NSE", "BSE", "RBI", "Company IR")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(ok: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * ok / total, 1)


def _error_rate(success: int, failure: int) -> float:
    n = success + failure
    if n <= 0:
        return 0.0
    return round(100.0 * failure / n, 1)


def _success_icon(ok: bool | None, *, warn: bool = False) -> str:
    if ok is True and not warn:
        return "ok"
    if ok is True and warn:
        return "warn"
    if ok is False:
        return "error"
    return "unknown"


def collector_health_rows() -> list[dict[str, Any]]:
    """Per-collector Success / Last Run / Latency / Queue / Error Rate."""
    try:
        from live_data import store as lidi_store
        from live_data.production import collectors as lidi_collectors

        health = lidi_store.get_collector_health() or {}
        last = lidi_store.get_last_run() or {}
        stages = last.get("stages") or {}
    except Exception:
        health, stages = {}, {}

    # Soft queue depth hints from IR downloads / backfill
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        qlen = int(bf_queue.backlog_stats().get("queue_length") or 0)
    except Exception:
        qlen = 0

    rows = []
    for cid, sid, name, source in COLLECTOR_DISPLAY:
        h = health.get(cid) or {}
        # Also match by source field
        if not h:
            for hid, hh in (health or {}).items():
                if str(hh.get("source") or "") == sid or sid in hid:
                    h = hh
                    cid = hid
                    break
        st = stages.get(sid) or {}
        succ = int(h.get("success_count") or 0)
        fail = int(h.get("failure_count") or 0)
        err = _error_rate(succ, fail)
        last_ok = st.get("ok")
        if last_ok is None:
            last_ok = bool(h.get("last_success")) and (
                not h.get("last_failure")
                or str(h.get("last_success") or "") >= str(h.get("last_failure") or "")
            )
        warn = err >= 5.0 or bool(st.get("fallback"))
        meta = h.get("metadata") or {}
        latency = meta.get("latency_ms") or st.get("latency_ms")
        # IR backlog uses backfill queue as soft signal; others 0 unless stage says pending
        queue_depth = int(st.get("queue") or meta.get("queue") or 0)
        if sid == "company_ir":
            queue_depth = max(queue_depth, min(qlen, 99))
        elif sid == "bse_corporate_actions" and warn:
            queue_depth = max(queue_depth, 1)

        last_run = h.get("last_success") or h.get("last_failure") or st.get("finished_at")
        rows.append(
            {
                "collector_id": cid,
                "source_id": sid,
                "collector": name,
                "source": source,
                "success": _success_icon(bool(last_ok), warn=warn),
                "success_bool": bool(last_ok) and not warn,
                "last_run": last_run,
                "latency_ms": latency,
                "latency_s": round(float(latency) / 1000.0, 1) if latency is not None else None,
                "queue": queue_depth,
                "error_rate_pct": err,
                "success_count": succ,
                "failure_count": fail,
                "last_error": (h.get("last_error") or st.get("error") or "")[:160] or None,
                "mode": st.get("mode") or meta.get("mode"),
            }
        )
    return rows


def source_reliability() -> list[dict[str, Any]]:
    """Aggregate reliability by vendor/source family."""
    rows = collector_health_rows()
    # Yahoo from KF HD live collectors
    yahoo = {"source": "Yahoo", "success": 0, "failure": 0}
    try:
        from knowledge_factory.historical_depth import store as hd_store

        last = hd_store.get_report("historical_backfill_last") or {}
        for r in last.get("rows") or []:
            live = r.get("live") or {}
            if live.get("status") == "ok" or r.get("status") == "ok":
                yahoo["success"] += 1
            elif live.get("errors") or r.get("status") == "error":
                yahoo["failure"] += 1
            else:
                yahoo["success"] += 1
        # Also count fixture-ok as soft yahoo N/A — prefer live report only
    except Exception:
        pass

    by_src: dict[str, dict[str, int]] = {k: {"success": 0, "failure": 0} for k in SOURCE_KEYS}
    by_src["Yahoo"] = yahoo
    for r in rows:
        src = r.get("source") or "Other"
        if src not in by_src:
            by_src[src] = {"success": 0, "failure": 0}
        by_src[src]["success"] += int(r.get("success_count") or 0)
        by_src[src]["failure"] += int(r.get("failure_count") or 0)

    out = []
    for src in SOURCE_KEYS:
        b = by_src.get(src) or {"success": 0, "failure": 0}
        rate = _pct(b["success"], b["success"] + b["failure"])
        if b["success"] + b["failure"] == 0:
            rate = None
        out.append(
            {
                "source": src,
                "reliability_pct": rate,
                "success_count": b["success"],
                "failure_count": b["failure"],
            }
        )
    return out


def coverage_heat_map(*, entities: list[str] | None = None) -> list[dict[str, Any]]:
    """Dataset category coverage across the universe."""
    from knowledge_factory.historical_depth import store as hd_store
    from knowledge_factory.historical_depth.universe_priority import supported_universe

    universe = entities or supported_universe()
    n = len(universe) or 1

    cats = {
        "OHLCV": 0,
        "Financials": 0,
        "Corporate Actions": 0,
        "Annual Reports": 0,
        "Presentations": 0,
        "Transcripts": 0,
        "ESG": 0,
        "Embeddings": 0,
        "Shareholding": 0,
    }

    for e in universe:
        prices = hd_store.get_series("prices", e) or {}
        if len(prices.get("records") or []) >= 12:
            cats["OHLCV"] += 1
        annual = hd_store.get_series("financials_annual", e) or {}
        quarterly = hd_store.get_series("financials_quarterly", e) or {}
        if len(annual.get("records") or []) >= 3 and len(quarterly.get("records") or []) >= 4:
            cats["Financials"] += 1
        actions = hd_store.get_series("corporate_actions", e) or {}
        if actions.get("records"):
            cats["Corporate Actions"] += 1
        sh = hd_store.get_series("shareholding", e) or {}
        if sh.get("records"):
            cats["Shareholding"] += 1
        try:
            from live_data import store as lidi_store

            docs = (lidi_store.get_object("company_ir", e) or {}).get("documents") or []
            types = {str(d.get("doc_type")) for d in docs}
            if "annual_report" in types:
                cats["Annual Reports"] += 1
            if "investor_presentation" in types:
                cats["Presentations"] += 1
            if "earnings_transcript" in types:
                cats["Transcripts"] += 1
            if "esg_report" in types:
                cats["ESG"] += 1
        except Exception:
            pass
        try:
            from continuous_gather_learn import persist as cgl_persist

            if cgl_persist.get_embedding(e).get("vector"):
                cats["Embeddings"] += 1
        except Exception:
            pass

    return [{"dataset": k, "coverage_pct": _pct(v, n), "covered": v, "universe": n} for k, v in cats.items()]


def coverage_by_index() -> list[dict[str, Any]]:
    """Hard-complete coverage by Nifty tiers (liquid universe first)."""
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth.universe_priority import (
        nifty_50,
        nifty_500,
        nifty_next_50,
        supported_universe,
    )

    q = bf_queue.load_queue()
    done = {
        str(c.get("company") or "").upper()
        for c in (q.get("companies") or [])
        if str(c.get("status")) in {bf_queue.STATUS_MAINTENANCE, bf_queue.STATUS_COMPLETE}
    }

    def _row(label: str, members: list[str]) -> dict[str, Any]:
        m = [x.upper() for x in members]
        covered = sum(1 for x in m if x in done)
        return {
            "index": label,
            "universe": len(m),
            "covered": covered,
            "coverage_pct": _pct(covered, len(m) or 1),
            "remaining": max(0, len(m) - covered),
        }

    n50 = nifty_50()
    nnext = nifty_next_50()
    n500 = nifty_500()
    n500_rest = [x for x in n500 if x not in set(n50) | set(nnext)]
    # Placeholders for broader boards until registries expand
    all_u = supported_universe()
    return [
        _row("NIFTY 50", n50),
        _row("NIFTY Next 50", nnext),
        _row("NIFTY 500", n500),
        _row("NIFTY 500 (ex-100)", n500_rest),
        {
            "index": "NSE Mainboard",
            "universe": len(all_u),
            "covered": len([x for x in all_u if x.upper() in done]),
            "coverage_pct": _pct(len([x for x in all_u if x.upper() in done]), len(all_u) or 1),
            "remaining": max(0, len(all_u) - len([x for x in all_u if x.upper() in done])),
            "note": "Currently = supported Nifty 500 path",
        },
        {
            "index": "SME",
            "universe": 0,
            "covered": 0,
            "coverage_pct": 0.0,
            "remaining": 0,
            "note": "Registry pending — placeholder",
        },
        {
            "index": "BSE-only",
            "universe": 0,
            "covered": 0,
            "coverage_pct": 0.0,
            "remaining": 0,
            "note": "Registry pending — placeholder",
        },
    ]


def backfill_throughput() -> dict[str, Any]:
    """How quickly the backlog is shrinking."""
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth import store as hd_store

    stats = bf_queue.backlog_stats()
    state = bf_queue.load_engine_state()
    last = hd_store.get_report("historical_backfill_last") or {}
    daily = hd_store.get_report("backfill_daily_throughput") or {}
    day = datetime.now(timezone.utc).date().isoformat()
    today = daily.get(day) or {}

    companies_today = int(state.get("companies_processed_today") or today.get("companies") or 0)
    years_today = float(today.get("years_added") or 0.0)
    docs_today = int(today.get("documents") or 0)
    extracts_today = int(today.get("extracts") or 0)

    # Infer from last batch if daily rollup empty
    if companies_today and years_today <= 0:
        for r in last.get("rows") or []:
            years_today += float(r.get("history_years") or 0)

    eta = bf_queue.eta_days(processed_today=companies_today or None)
    return {
        "companies_completed_today": companies_today,
        "average_years_added_today": round(years_today, 1),
        "documents_downloaded_today": docs_today,
        "knowledge_extracts_today": extracts_today,
        "remaining_backlog": stats.get("remaining"),
        "estimated_completion_days": eta,
        "last_batch_processed": last.get("processed"),
        "last_batch_runtime_s": last.get("runtime_seconds"),
        "mode": stats.get("mode"),
        "day": day,
    }


def record_throughput_sample(*, companies: int = 0, years: float = 0.0, documents: int = 0, extracts: int = 0) -> None:
    """Accumulate today's throughput counters (best-effort)."""
    try:
        from knowledge_factory.historical_depth import store as hd_store

        day = datetime.now(timezone.utc).date().isoformat()
        daily = hd_store.get_report("backfill_daily_throughput") or {}
        row = dict(daily.get(day) or {})
        row["companies"] = int(row.get("companies") or 0) + int(companies)
        row["years_added"] = float(row.get("years_added") or 0) + float(years)
        row["documents"] = int(row.get("documents") or 0) + int(documents)
        row["extracts"] = int(row.get("extracts") or 0) + int(extracts)
        row["updated_at"] = _now()
        daily[day] = row
        # Keep ~60 days
        keys = sorted(k for k in daily.keys() if k[:1].isdigit())
        for k in keys[:-60]:
            daily.pop(k, None)
        hd_store.put_report("backfill_daily_throughput", daily)
    except Exception:
        return


def ops_dashboard() -> dict[str, Any]:
    """Full operational board for Mission Control / CGL."""
    collectors = collector_health_rows()
    sources = source_reliability()
    heat = coverage_heat_map()
    by_index = coverage_by_index()
    throughput = backfill_throughput()
    try:
        from knowledge_factory.historical_depth.coverage_audit import latest_audit

        audit = latest_audit()
    except Exception:
        audit = None
    degraded = [c for c in collectors if c.get("success") in {"warn", "error"}]

    institutional: dict[str, Any] = {}
    try:
        from institutional_data.production import dashboard as id_dash

        institutional = id_dash()
    except Exception as exc:  # noqa: BLE001
        institutional = {"ok": False, "error": str(exc)[:160]}

    # Prefer rolling reliability trends when present
    rel_trends = institutional.get("source_reliability_trends") or []
    if rel_trends:
        sources = [
            {
                "source": r.get("source"),
                "reliability_pct": r.get("availability_pct"),
                "failure_pct": r.get("failure_pct"),
                "latency_ms_avg": r.get("latency_ms_avg"),
                "coverage_pct_avg": r.get("coverage_pct_avg"),
                "samples_7d": r.get("samples_7d"),
            }
            for r in rel_trends
        ] or sources

    reconcile = None
    try:
        from knowledge_factory.historical_depth.coverage_reconcile import latest_reconciliation

        reconcile = latest_reconciliation()
    except Exception:
        reconcile = None

    dataset = (reconcile or {}).get("dataset_coverage") or {}
    evidence_backlog = (reconcile or {}).get("evidence_backlog") or (
        reconcile or {}
    ).get("incomplete_preview") or []
    # Prefer heat map / connector coverage for data-plane truth
    hist_coverage = {
        "ohlcv_pct": dataset.get("ohlcv_pct")
        if dataset.get("ohlcv_pct") is not None
        else next((r.get("coverage_pct") for r in heat if r.get("dataset") == "OHLCV"), None),
        "financials_pct": (institutional.get("financial_coverage") or {}).get("coverage_pct")
        if institutional.get("financial_coverage")
        else dataset.get("financials_pct"),
        "shareholding_pct": (institutional.get("shareholding_coverage") or {}).get("coverage_pct")
        if institutional.get("shareholding_coverage")
        else dataset.get("shareholding_pct"),
        "ir_pct": (institutional.get("ir_coverage") or {}).get("coverage_pct"),
        "verified_hard_coverage_pct": (reconcile or {}).get("verified_hard_coverage_pct"),
        "average_years": (reconcile or {}).get("average_history_years")
        or (institutional.get("kpis") or {}).get("average_historical_years"),
        "incomplete": (reconcile or {}).get("incomplete"),
        "authority": (reconcile or {}).get("authority") or "evidence_based_completion",
    }

    scheduler_status = "healthy"
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        eng = bf_queue.load_engine_state()
        if eng.get("maintenance_only") and not (reconcile or {}).get("maintenance_allowed"):
            scheduler_status = "misaligned"  # control plane claims maintenance; data plane disagrees
        elif eng.get("mode") == "deep_backfill":
            scheduler_status = "backfilling"
    except Exception:
        pass

    return {
        "ops_version": OPS_VERSION,
        "generated_at": _now(),
        "collector_health": collectors,
        "source_reliability": sources,
        "coverage_heat_map": heat,
        "coverage_by_index": by_index,
        "backfill_throughput": throughput,
        "coverage_audit": audit,
        "coverage_reconcile": reconcile,
        "evidence_backlog": evidence_backlog,
        "evidence_based_completion": {
            "authority": "evidence_based_completion",
            "incomplete": (reconcile or {}).get("incomplete"),
            "verified_complete": (reconcile or {}).get("verified_complete"),
            "backlog": evidence_backlog,
            "note": "Each company shows evidence checklist + hard coverage % + why incomplete",
        },
        "degraded_collectors": len(degraded),
        "financial_coverage": institutional.get("financial_coverage"),
        "shareholding_coverage": institutional.get("shareholding_coverage"),
        "ir_coverage": institutional.get("ir_coverage"),
        "checkpoint_status": institutional.get("checkpoint_status"),
        "storage_usage": (institutional.get("checkpoint_status") or {}).get("storage"),
        "persistent_queue": institutional.get("persistent_queue"),
        "repair_queue": ((institutional.get("kpis") or {}).get("repair_queue_size"))
        or len(((reconcile or {}).get("incomplete_preview") or [])),
        "kpis": institutional.get("kpis"),
        "living_universe_ops": institutional.get("living_universe"),
        "recovery": institutional.get("recovery"),
        "historical_depth": {
            "average_years": hist_coverage.get("average_years"),
            "completeness_pct": hist_coverage.get("verified_hard_coverage_pct"),
        },
        "historical_coverage_verified": hist_coverage,
        "operational_status": {
            "scheduler": scheduler_status,
            "collectors": {
                "degraded": len(degraded),
                "rows": [
                    {"collector": c.get("collector"), "success": c.get("success"), "error_rate_pct": c.get("error_rate_pct")}
                    for c in collectors
                ],
            },
            "historical_coverage": hist_coverage,
            "maintenance_allowed": (reconcile or {}).get("maintenance_allowed"),
            "evidence_backlog_size": len(evidence_backlog),
        },
        "knowledge_density": {
            "extracts": (institutional.get("kpis") or {}).get("knowledge_extracts"),
            "embeddings": (institutional.get("kpis") or {}).get("embeddings"),
        },
        "north_star": "Evidence-based completion — checklist from stored datasets, not queue state",
        "focus": "control-plane vs data-plane honesty",
    }
