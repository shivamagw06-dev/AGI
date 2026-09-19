"""Dashboard builders — pure aggregations over stored release artifacts."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.observability.schema import DECISION_BUCKETS


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct(n: int, d: int) -> float:
    if d <= 0:
        return 0.0
    return round(100.0 * n / d, 1)


def _normalize_decision(label: str | None) -> str:
    d = str(label or "").strip()
    if not d:
        return "Other"
    low = d.lower()
    for bucket in DECISION_BUCKETS:
        if bucket.lower() == low:
            return bucket
    if "high conviction" in low:
        return "High Conviction"
    if "constructive" in low:
        return "Constructive"
    if "neutral" in low:
        return "Neutral"
    if "watch" in low:
        return "Watchlist"
    if "defer" in low or "inconclusive" in low:
        return "Deferred" if "defer" in low else "Inconclusive"
    if "cautious" in low or "avoid" in low:
        return "Cautious"
    return "Other"


def executive_dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get("rows") or []
    summary = bundle.get("summary") or {}
    health = summary.get("health") or {}
    phase6 = bundle.get("phase6") or {}
    drift = bundle.get("drift") or {}

    n = len(rows) or int(bundle.get("n") or 0)
    gov_ok = None
    if phase6:
        crit = int(phase6.get("critical_rule_failures") or 0)
        assertions = phase6.get("governance_assertions") or phase6.get("board") or []
        if assertions:
            fails = sum(1 for a in assertions if a.get("status") == "FAIL")
            gov_ok = _pct(len(assertions) - fails, len(assertions))
        else:
            gov_ok = 100.0 if crit == 0 else 0.0

    unknown = int((drift.get("unexpected") or (drift.get("by_reason_code") or {}).get("UNKNOWN") or 0))
    avg_ready = health.get("average_readiness")
    if avg_ready is None:
        vals = [_f(r.get("recommendation_readiness")) for r in rows]
        vals = [v for v in vals if v is not None]
        avg_ready = round((sum(vals) / len(vals)) / 100.0, 4) if vals else None
    # Display as percent when stored 0–1
    avg_ready_pct = None
    if avg_ready is not None:
        avg_ready_pct = round(avg_ready * 100, 1) if avg_ready <= 1.5 else round(avg_ready, 1)

    runtime_ms = health.get("average_runtime_ms") or summary.get("average_runtime_ms")
    if runtime_ms is None:
        rts = []
        for r in rows:
            t = (r.get("timing") or {}).get("total_ms") or r.get("runtime_ms")
            if t is not None:
                rts.append(float(t))
        runtime_ms = int(sum(rts) / len(rts)) if rts else None

    budget_pass = (drift.get("budget") or {}).get("passed")
    status = "PASS"
    if phase6 and int(phase6.get("critical_rule_failures") or 0) > 0:
        status = "FAIL"
    if drift and (unknown > 0 or budget_pass is False):
        status = "FAIL"
    if drift is None and phase6 is None and n == 0:
        status = "UNKNOWN"

    return {
        "release": bundle.get("release_id"),
        "status": status,
        "companies_tested": n,
        "governance_pct": gov_ok,
        "unknown_drift": unknown,
        "average_readiness_pct": avg_ready_pct,
        "runtime_s": round(runtime_ms / 1000.0, 2) if runtime_ms else None,
        "budget_passed": budget_pass,
        "phase6_present": bool(phase6),
        "drift_present": bool(drift),
    }


def recommendation_distribution(bundle: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {b: 0 for b in DECISION_BUCKETS}
    for r in bundle.get("rows") or []:
        bucket = _normalize_decision(r.get("decision"))
        counts[bucket] = counts.get(bucket, 0) + 1
    ordered = {b: counts.get(b, 0) for b in DECISION_BUCKETS if counts.get(b, 0) or b in {
        "High Conviction", "Constructive", "Neutral", "Watchlist", "Deferred"
    }}
    return {"distribution": ordered, "n": sum(counts.values())}


def sector_dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    by_sec: dict[str, list[dict[str, Any]]] = {}
    for r in bundle.get("rows") or []:
        by_sec.setdefault(str(r.get("sector") or "Unknown"), []).append(r)
    table = []
    for sector, items in sorted(by_sec.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        n = len(items)
        passed = sum(1 for r in items if str(r.get("gate") or "").upper() == "PASS" or r.get("status") == "COMPLETED")
        ready = [_f(r.get("recommendation_readiness")) for r in items]
        ready = [v for v in ready if v is not None]
        rts = []
        for r in items:
            t = (r.get("timing") or {}).get("total_ms") or r.get("runtime_ms")
            if t is not None:
                rts.append(float(t))
        table.append(
            {
                "sector": sector,
                "n": n,
                "pass_pct": _pct(passed, n),
                "avg_readiness_pct": round(sum(ready) / len(ready), 1) if ready else None,
                "avg_runtime_s": round((sum(rts) / len(rts)) / 1000.0, 2) if rts else None,
            }
        )
    return {"sectors": table, "sector_count": len(table)}


def governance_dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    phase6 = bundle.get("phase6") or {}
    assertions = phase6.get("governance_assertions") or []
    if not assertions and phase6.get("board"):
        assertions = [
            {
                "rule_id": b.get("rule_id"),
                "status": b.get("status"),
                "pass": None,
                "fail": None,
                "skip": None,
            }
            for b in phase6["board"]
        ]
    n = int(bundle.get("n") or len(bundle.get("rows") or []) or 0)
    rows = []
    for a in assertions:
        p = a.get("pass")
        f = a.get("fail")
        # When pass/fail counts absent, treat PASS as n/n
        if p is None and a.get("status") == "PASS":
            p, f = n, 0
        elif p is None and a.get("status") == "FAIL":
            p, f = 0, n
        elif p is None:
            p, f = 0, 0
        rows.append(
            {
                "rule_id": a.get("rule_id"),
                "status": a.get("status"),
                "pass": p,
                "fail": f or 0,
                "skip": a.get("skip") or 0,
                "display": f"{p} / {n}" if n else f"{p}",
            }
        )
    fails = sum(1 for r in rows if r["status"] == "FAIL")
    overall = _pct(len(rows) - fails, len(rows)) if rows else None
    return {
        "present": bool(phase6),
        "rules": rows,
        "overall_pct": overall,
        "critical_rule_failures": phase6.get("critical_rule_failures"),
        "spec_version": phase6.get("spec_version"),
    }


def drift_dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    drift = bundle.get("drift") or {}
    if not drift:
        return {"present": False}
    return {
        "present": True,
        "previous_release": drift.get("previous_release"),
        "current_release": drift.get("current_release"),
        "recommendation_changes": drift.get("recommendations_changed"),
        "expected": drift.get("expected"),
        "unexpected": drift.get("unexpected"),
        "budget": "PASS" if (drift.get("budget") or {}).get("passed") else "FAIL",
        "budget_breaches": (drift.get("budget") or {}).get("breaches") or [],
        "by_reason_code": drift.get("by_reason_code") or {},
        "requires_review": (drift.get("review_queue") or {}).get("requires_review"),
    }


def performance_dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get("rows") or []
    totals: list[float] = []
    modules: dict[str, list[float]] = {
        "company_pack_ms": [],
        "groww_price_ms": [],
        "decision_engine_ms": [],
        "company_intelligence_ms": [],
    }
    for r in rows:
        timing = r.get("timing") or {}
        total = timing.get("total_ms") or r.get("runtime_ms")
        if total is not None:
            totals.append(float(total))
        for k in modules:
            if timing.get(k) is not None:
                modules[k].append(float(timing[k]))

    def _avg(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 1) if vals else None

    def _p95(vals: list[float]) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        idx = min(len(s) - 1, max(0, int(round(0.95 * (len(s) - 1)))))
        return round(s[idx], 1)

    module_avg = {k: _avg(v) for k, v in modules.items() if v}
    # Map to friendly names for "slowest module"
    labels = {
        "company_pack_ms": "Company Pack",
        "groww_price_ms": "Groww Price",
        "decision_engine_ms": "Decision Engine",
        "company_intelligence_ms": "Company Intelligence",
    }
    slowest = None
    fastest = None
    if module_avg:
        slowest_key = max(module_avg, key=module_avg.get)
        fastest_key = min(module_avg, key=module_avg.get)
        slowest = labels.get(slowest_key, slowest_key)
        fastest = labels.get(fastest_key, fastest_key)

    avg_ms = _avg(totals)
    return {
        "average_runtime_ms": int(avg_ms) if avg_ms is not None else None,
        "average_runtime_s": round(avg_ms / 1000.0, 2) if avg_ms is not None else None,
        "p95_runtime_ms": _p95(totals),
        "p95_runtime_s": round((_p95(totals) or 0) / 1000.0, 2) if totals else None,
        "slowest_module": slowest,
        "fastest_module": fastest,
        "module_averages_ms": {labels.get(k, k): v for k, v in module_avg.items()},
        "n": len(totals),
    }


def coverage_dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    """Evidence/coverage proxies from stored ticker rows — no re-ingestion."""
    rows = bundle.get("rows") or []
    n = len(rows) or 1

    def rate(pred) -> float:
        return _pct(sum(1 for r in rows if pred(r)), n)

    # Approximate pillar coverage from available fields / failure reasons / evidence class
    financials = rate(
        lambda r: (r.get("financial_quality") or 0) >= 5
        or str(r.get("evidence_class") or "") == "Complete"
        or (
            str((r.get("failure") or {}).get("reason") or "")
            not in {"FINANCIALS_OR_FILING_MISSING"}
            and str(r.get("gate") or "").upper() == "PASS"
        )
    )
    ownership = rate(
        lambda r: str((r.get("failure") or {}).get("reason") or "") != "SHAREHOLDING_MISSING"
        and (
            str(r.get("evidence_class") or "") in {"Complete", "Partial"}
            or str(r.get("gate") or "").upper() == "PASS"
        )
    )
    valuation = rate(
        lambda r: (r.get("valuation") is not None and float(r.get("valuation") or 0) > 0)
        or str((r.get("failure") or {}).get("reason") or "") != "VALUATION_MISSING"
    )
    macro = rate(lambda r: r.get("macro") is not None)
    # News proxy: not failed + pack/provenance present
    news = rate(
        lambda r: bool(r.get("pack_present") or r.get("knowledge_snapshot") or r.get("live_price"))
    )

    # Prefer summary coverage block when present
    summary_cov = (bundle.get("summary") or {}).get("coverage") or {}
    evidence = summary_cov.get("evidence_coverage") or {}

    return {
        "financials_pct": financials,
        "ownership_pct": ownership,
        "valuation_pct": valuation,
        "macro_pct": macro,
        "news_pct": news,
        "evidence_complete": evidence.get("Complete"),
        "evidence_partial": evidence.get("Partial"),
        "evidence_insufficient": evidence.get("Insufficient"),
        "n": len(rows),
    }


def historical_trends(release_ids: list[str]) -> dict[str, Any]:
    """Lightweight multi-release trend from stored summaries only."""
    points = []
    for rid in release_ids:
        bundle = __import__(
            "institutional_evaluation_lab.observability.loaders", fromlist=["load_release_bundle"]
        ).load_release_bundle(rid)
        if not bundle.get("found"):
            continue
        exe = executive_dashboard(bundle)
        points.append(
            {
                "release": rid,
                "status": exe.get("status"),
                "companies": exe.get("companies_tested"),
                "average_readiness_pct": exe.get("average_readiness_pct"),
                "runtime_s": exe.get("runtime_s"),
                "unknown_drift": exe.get("unknown_drift"),
                "governance_pct": exe.get("governance_pct"),
            }
        )
    return {"releases": points, "n": len(points)}
