"""Weekly coverage audit — finds gaps and builds an automatic repair queue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.completion import evaluate_completion, history_years
from knowledge_factory.historical_depth.universe_priority import (
    nifty_50,
    prioritised_universe,
    supported_universe,
)

AUDIT_REPORT = "weekly_coverage_audit"
REPAIR_QUEUE = "coverage_repair_queue"
AUDIT_VERSION = "coverage-audit-v1.0.0"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def latest_audit() -> dict[str, Any] | None:
    return hd_store.get_report(AUDIT_REPORT)


def load_repair_queue() -> dict[str, Any]:
    return hd_store.get_report(REPAIR_QUEUE) or {"items": [], "updated_at": None}


def should_run_weekly_audit(*, force: bool = False) -> bool:
    if force:
        return True
    last = latest_audit() or {}
    at = last.get("generated_at")
    if not at:
        return True
    try:
        ts = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
        return _now() - ts >= timedelta(days=7)
    except Exception:
        return True


def run_coverage_audit(
    *,
    entities: list[str] | None = None,
    force: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Scan universe for gaps; persist audit + repair queue.

    Answers:
    - missing historical periods
    - incomplete financials
    - failed document downloads
    - missing embeddings
    - failed QA
    - collectors degraded (via ops soft import)
    """
    if not force and not should_run_weekly_audit(force=False):
        last = latest_audit() or {}
        return {**last, "skipped": True, "reason": "audit_fresh_within_7d"}

    universe = entities or prioritised_universe()
    if limit:
        universe = universe[: int(limit)]

    missing_periods: list[dict[str, Any]] = []
    incomplete_financials: list[dict[str, Any]] = []
    failed_documents: list[dict[str, Any]] = []
    missing_embeddings: list[dict[str, Any]] = []
    qa_failures: list[dict[str, Any]] = []
    repair: list[dict[str, Any]] = []

    for e in universe:
        ev = evaluate_completion(e)
        dims = ev.get("dimensions") or {}
        years = history_years(e)
        target = float(ev.get("effective_target_years") or 15)

        if years + 1e-9 < target:
            missing_periods.append(
                {"company": e, "years": years, "target": target, "gap_years": round(target - years, 2)}
            )
            repair.append({"company": e, "reason": "missing_historical_periods", "priority": 1})

        fin = dims.get("financial_statements") or {}
        if fin.get("status") != "complete":
            incomplete_financials.append({"company": e, "detail": fin.get("detail")})
            repair.append({"company": e, "reason": "incomplete_financials", "priority": 2})

        emb = dims.get("embeddings") or {}
        if emb.get("status") != "complete":
            missing_embeddings.append({"company": e})
            repair.append({"company": e, "reason": "missing_embeddings", "priority": 3})

        qa = dims.get("qa") or {}
        if qa.get("status") != "complete":
            qa_failures.append({"company": e, "detail": qa.get("detail")})
            repair.append({"company": e, "reason": "qa_failed", "priority": 1})

        # Soft IR download failures from attempt meta
        attempts = (hd_store.get_report(f"backfill_attempts_{e}") or {}).get("dimensions") or {}
        for key in ("annual_reports", "investor_presentations"):
            att = attempts.get(key) or {}
            if att.get("status") == "empty" or (att.get("detail") or "").startswith("http"):
                failed_documents.append({"company": e, "doc": key, "detail": att.get("detail")})
                repair.append({"company": e, "reason": f"document_{key}", "priority": 4})

    # Collector degradation over last week (soft)
    degraded_collectors: list[dict[str, Any]] = []
    try:
        from continuous_gather_learn.ops_observability import collector_health_rows

        for row in collector_health_rows():
            if row.get("success") in {"warn", "error"} or float(row.get("error_rate_pct") or 0) >= 5:
                degraded_collectors.append(
                    {
                        "collector": row.get("collector"),
                        "error_rate_pct": row.get("error_rate_pct"),
                        "last_error": row.get("last_error"),
                    }
                )
    except Exception:
        pass

    # Deduplicate repair queue by company+reason, prefer Nifty 50
    n50 = set(nifty_50())
    uniq: dict[str, dict[str, Any]] = {}
    for item in repair:
        key = f"{item['company']}|{item['reason']}"
        item = {
            **item,
            "tier_boost": 0 if item["company"] in n50 else 1,
            "enqueued_at": _now_iso(),
        }
        uniq.setdefault(key, item)
    repair_items = sorted(
        uniq.values(),
        key=lambda x: (int(x.get("tier_boost") or 0), int(x.get("priority") or 9), str(x.get("company"))),
    )

    # Auto-enqueue top repair items onto backfill queue (hard gaps only)
    enqueued = []
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        for item in repair_items:
            if item.get("reason") in {
                "missing_historical_periods",
                "incomplete_financials",
                "missing_embeddings",
                "qa_failed",
            }:
                bf_queue.enqueue_company(str(item["company"]), reason=f"audit:{item['reason']}")
                enqueued.append(item["company"])
                if len(enqueued) >= 40:
                    break
    except Exception:
        pass

    report = {
        "audit_version": AUDIT_VERSION,
        "generated_at": _now_iso(),
        "universe_scanned": len(universe),
        "missing_historical_periods": missing_periods[:200],
        "incomplete_financials": incomplete_financials[:200],
        "failed_documents": failed_documents[:200],
        "missing_embeddings": missing_embeddings[:200],
        "qa_failures": qa_failures[:200],
        "degraded_collectors": degraded_collectors,
        "counts": {
            "missing_historical_periods": len(missing_periods),
            "incomplete_financials": len(incomplete_financials),
            "failed_documents": len(failed_documents),
            "missing_embeddings": len(missing_embeddings),
            "qa_failures": len(qa_failures),
            "degraded_collectors": len(degraded_collectors),
            "repair_queue": len(repair_items),
            "auto_enqueued": len(set(enqueued)),
        },
        "repair_queue_preview": repair_items[:50],
        "skipped": False,
    }
    hd_store.put_report(AUDIT_REPORT, report)
    hd_store.put_report(
        REPAIR_QUEUE,
        {
            "items": repair_items[:500],
            "updated_at": _now_iso(),
            "auto_enqueued": list(dict.fromkeys(enqueued))[:40],
            "audit_generated_at": report["generated_at"],
        },
    )
    return report


def maybe_run_weekly_audit() -> dict[str, Any]:
    """Soft entrypoint for CGL cycles — runs at most weekly."""
    return run_coverage_audit(force=False)
