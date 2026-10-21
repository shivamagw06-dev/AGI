"""Coverage-derived backlog — queue is derived from verified data, not authoritative.

Recomputes missing work from required datasets → coverage engine → backlog → queue.
Maintenance mode cannot activate from an empty queue alone.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from knowledge_factory.historical_depth import queue as bf_queue
from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.completion import (
    evidence_based_completion,
    history_years,
)
from knowledge_factory.historical_depth.universe_priority import prioritised_universe

RECONCILE_REPORT = "coverage_reconciliation"
RECONCILE_VERSION = "coverage-reconcile-v1.1.0"

# Universe hard-coverage threshold before maintenance is allowed.
MAINTENANCE_HARD_COVERAGE_PCT = float(os.getenv("KF_HD_MAINTENANCE_HARD_COVERAGE_PCT") or "95")
# Minimum average verified OHLCV years across universe.
MAINTENANCE_MIN_AVG_YEARS = float(os.getenv("KF_HD_MAINTENANCE_MIN_AVG_YEARS") or "10")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_company(entity: str) -> dict[str, Any]:
    """Evidence-based verified-coverage check for backlog + maintenance gates."""
    evidence = evidence_based_completion(entity)
    missing = list(evidence.get("missing") or [])
    verified_ok = bool(evidence.get("complete"))
    return {
        "company": entity.upper(),
        "verified_ok": verified_ok,
        "complete": verified_ok,
        "missing": missing,
        "missing_labels": evidence.get("missing_labels") or [],
        "why_incomplete": evidence.get("why_incomplete"),
        "why_in_backlog": evidence.get("why_in_backlog"),
        "checklist": evidence.get("checklist") or [],
        "evidence": evidence.get("evidence") or {},
        "years": evidence.get("years") or 0.0,
        "hard_pct": evidence.get("hard_coverage_pct"),
        "hard_coverage_pct": evidence.get("hard_coverage_pct"),
        "authority": "evidence_based_completion",
        "evaluation": evidence.get("evaluation"),
        "evidence_card": evidence,
    }


def connectors_healthy_enough() -> dict[str, Any]:
    """Refuse maintenance if critical collectors are actively failing.

    Unknown / never-run collectors do not block (common right after redeploy).
    Only count explicit recent failures with evidence.
    """
    try:
        from continuous_gather_learn.ops_observability import collector_health_rows

        rows = collector_health_rows()
    except Exception:
        return {"ok": True, "degraded": [], "note": "health_unavailable"}
    critical = {"BSE Actions", "NSE Bhavcopy", "Company IR"}
    degraded = []
    for r in rows:
        if r.get("collector") not in critical:
            continue
        # No run yet → unknown, not degraded
        if not r.get("last_run") and int(r.get("failure_count") or 0) == 0:
            continue
        err = float(r.get("error_rate_pct") or 0)
        if r.get("success") == "error" or err >= 50.0:
            degraded.append(r.get("collector"))
        elif r.get("success") == "warn" and err >= 20.0:
            degraded.append(r.get("collector"))
    # Institutional connector reliability — only with enough samples
    fin_fail = sh_fail = False
    try:
        from institutional_data.reliability.scores import reliability_dashboard

        for r in reliability_dashboard():
            samples = int(r.get("samples_7d") or 0)
            if samples < 3:
                continue
            if r.get("source") == "financial_statements" and float(r.get("failure_pct") or 0) >= 80:
                fin_fail = True
            if r.get("source") == "shareholding" and float(r.get("failure_pct") or 0) >= 80:
                sh_fail = True
    except Exception:
        pass
    ok = len(degraded) == 0 and not fin_fail and not sh_fail
    return {
        "ok": ok,
        "degraded": degraded,
        "financial_connector_failing": fin_fail,
        "shareholding_connector_failing": sh_fail,
    }


def reconcile_universe(
    *,
    entities: list[str] | None = None,
    limit: int | None = None,
    enqueue: bool = True,
) -> dict[str, Any]:
    """Scan universe, compare expected vs stored, rebuild backlog from reality."""
    universe = entities or prioritised_universe()
    if limit:
        universe = universe[: int(limit)]

    incomplete: list[dict[str, Any]] = []
    complete: list[dict[str, Any]] = []
    requeued: list[str] = []

    for e in universe:
        v = verify_company(e)
        if v["verified_ok"]:
            complete.append(
                {
                    "company": e,
                    "years": v["years"],
                    "hard_pct": v["hard_pct"],
                    "hard_coverage_pct": v.get("hard_coverage_pct"),
                    "complete": True,
                    "evidence": v.get("evidence"),
                }
            )
        else:
            incomplete.append(
                {
                    "company": e,
                    "missing": v["missing"],
                    "missing_labels": v.get("missing_labels") or [],
                    "why_incomplete": v.get("why_incomplete"),
                    "why_in_backlog": v.get("why_in_backlog") or v.get("why_incomplete"),
                    "checklist": v.get("checklist") or [],
                    "evidence": v.get("evidence") or {},
                    "years": v["years"],
                    "hard_pct": v["hard_pct"],
                    "hard_coverage_pct": v.get("hard_coverage_pct"),
                    "complete": False,
                }
            )
            if enqueue:
                reason_bits = v.get("missing") or ["incomplete"]
                bf_queue.enqueue_company(
                    e,
                    reason="evidence:" + ",".join(reason_bits[:5]),
                )
                # Force out of false maintenance
                try:
                    q = bf_queue.load_queue()
                    for row in q.get("companies") or []:
                        if str(row.get("company") or "").upper() == e.upper():
                            if str(row.get("status")) in {
                                bf_queue.STATUS_COMPLETE,
                                bf_queue.STATUS_MAINTENANCE,
                            }:
                                row["status"] = bf_queue.STATUS_PENDING
                                row["mode"] = "backfill"
                                row["reconcile_reopened"] = True
                                row["missing"] = v["missing"]
                                row["why_incomplete"] = v.get("why_incomplete")
                                row["hard_coverage_pct"] = v.get("hard_coverage_pct")
                                row["evidence"] = v.get("evidence")
                            break
                    bf_queue.save_queue(q)
                except Exception:
                    pass
                requeued.append(e)

    n = len(universe) or 1
    verified_pct = round(100.0 * len(complete) / n, 2)
    years = [float(c.get("years") or 0) for c in complete + incomplete] or [0.0]
    avg_years = round(sum(years) / len(years), 2)

    # Dataset coverage (data-plane)
    ohlcv = sum(1 for e in universe if history_years(e) >= 1 and (hd_store.get_series("prices", e) or {}).get("records"))
    fin = 0
    sh = 0
    for e in universe:
        a = hd_store.get_series("financials_annual", e) or {}
        q = hd_store.get_series("financials_quarterly", e) or {}
        if _institutional_financials(a, q):
            fin += 1
        if (hd_store.get_series("shareholding", e) or {}).get("records"):
            sh += 1

    health = connectors_healthy_enough()
    backlog_n = len(incomplete)
    can_maintain = (
        backlog_n == 0
        and verified_pct + 1e-9 >= MAINTENANCE_HARD_COVERAGE_PCT
        and avg_years + 1e-9 >= MAINTENANCE_MIN_AVG_YEARS
        and bool(health.get("ok"))
    )

    engine = bf_queue.load_engine_state()
    if can_maintain:
        engine = bf_queue.save_engine_state(
            {
                **engine,
                "mode": "maintenance",
                "deep_backfill_enabled": False,
                "maintenance_only": True,
                "completed_at": engine.get("completed_at") or _now(),
                "coverage_finished": False,
                "verified_gate": True,
                "note": "Verified coverage thresholds met — maintenance allowed",
            }
        )
    else:
        # Force deep backfill when reality disagrees with queue
        if engine.get("maintenance_only") or backlog_n > 0:
            engine = bf_queue.save_engine_state(
                {
                    **engine,
                    "mode": "deep_backfill",
                    "deep_backfill_enabled": True,
                    "maintenance_only": False,
                    "reopened_at": _now(),
                    "verified_gate": False,
                    "note": (
                        f"Coverage reconcile: backlog={backlog_n} verified={verified_pct}% "
                        f"avg_years={avg_years} connectors_ok={health.get('ok')}"
                    ),
                }
            )

    report = {
        "reconcile_version": RECONCILE_VERSION,
        "generated_at": _now(),
        "universe_scanned": len(universe),
        "verified_complete": len(complete),
        "incomplete": len(incomplete),
        "requeued": len(requeued),
        "verified_hard_coverage_pct": verified_pct,
        "average_history_years": avg_years,
        "dataset_coverage": {
            "ohlcv_pct": round(100.0 * ohlcv / n, 1),
            "financials_pct": round(100.0 * fin / n, 1),
            "shareholding_pct": round(100.0 * sh / n, 1),
        },
        "connectors": health,
        "maintenance_allowed": can_maintain,
        "maintenance_thresholds": {
            "hard_coverage_pct": MAINTENANCE_HARD_COVERAGE_PCT,
            "min_avg_years": MAINTENANCE_MIN_AVG_YEARS,
        },
        "incomplete_preview": incomplete[:40],
        "evidence_backlog": incomplete[:40],
        "requeued_preview": requeued[:40],
        "engine": {
            "mode": engine.get("mode"),
            "maintenance_only": engine.get("maintenance_only"),
        },
        "authority": "evidence_based_completion",
        "note": (
            "Completion is evidence-based: each company carries a checklist "
            "(OHLCV/Financials/CA/Shareholding/IR/Embeddings/QA). "
            "Queue is derived from missing evidence; never authoritative for maintenance."
        ),
    }
    hd_store.put_report(RECONCILE_REPORT, report)
    # Repair queue mirror
    try:
        from institutional_data.persistence.queue_persistence import QueuePersistence

        QueuePersistence().save_repair_queue(
            {
                "items": [
                    {
                        "company": row["company"],
                        "reason": "missing:" + ",".join(row.get("missing") or []),
                        "priority": 1,
                        "enqueued_at": _now(),
                    }
                    for row in incomplete[:500]
                ],
                "source": "coverage_reconcile",
                "updated_at": _now(),
            }
        )
    except Exception:
        pass
    return report


def _institutional_financials(annual: dict[str, Any], quarterly: dict[str, Any]) -> bool:
    """True only when statements look institutional — not price-proxy annuals."""
    a_recs = list(annual.get("records") or [])
    q_recs = list(quarterly.get("records") or [])
    if len(a_recs) < 3:
        return False

    def _is_statement(r: dict[str, Any]) -> bool:
        src = str(r.get("source") or "")
        payload = r.get("payload") or {}
        if src == "financial_connector":
            return True
        if payload.get("statement") in {"income", "balance", "cashflow"}:
            return True
        if payload.get("revenue") is not None or payload.get("net_income") is not None:
            return True
        accounts = payload.get("accounts") or {}
        if accounts.get("revenue") is not None or accounts.get("total_revenue") is not None:
            return True
        return False

    institutional_annual = sum(1 for r in a_recs if _is_statement(r))
    if institutional_annual < 3:
        return False
    # Quarterlies required for institutional completeness
    return len(q_recs) >= 4 and sum(1 for r in q_recs if _is_statement(r) or r.get("payload")) >= 2


def latest_reconciliation() -> dict[str, Any] | None:
    return hd_store.get_report(RECONCILE_REPORT)


def maybe_reconcile(*, enqueue: bool = True, max_age_minutes: float = 30.0) -> dict[str, Any]:
    """Throttle full reconciliation so batch loops stay responsive."""
    last = latest_reconciliation() or {}
    at = last.get("generated_at")
    if at:
        try:
            ts = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
            age_m = (datetime.now(timezone.utc) - ts).total_seconds() / 60.0
            if age_m < max_age_minutes and last.get("reconcile_version") == RECONCILE_VERSION:
                return {**last, "skipped": True, "reason": "fresh"}
        except Exception:
            pass
    return reconcile_universe(enqueue=enqueue)


def verified_universe_stats(*, sample_limit: int | None = None) -> dict[str, Any]:
    """Fast-ish data-plane stats for Mission Control (may sample large universes)."""
    universe = prioritised_universe()
    if sample_limit and len(universe) > sample_limit:
        # Prefer Nifty 50 first then sample rest
        from knowledge_factory.historical_depth.universe_priority import nifty_50

        n50 = nifty_50()
        rest = [e for e in universe if e not in set(n50)]
        universe = list(n50) + rest[: max(0, sample_limit - len(n50))]
    return reconcile_universe(entities=universe, enqueue=False)
