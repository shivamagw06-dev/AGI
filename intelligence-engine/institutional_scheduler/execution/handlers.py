"""Soft-wire workflow handlers — call existing packages; never modify them."""

from __future__ import annotations

from typing import Any

from institutional_scheduler import store


def _ok(payload: Any = None, **extra: Any) -> dict[str, Any]:
    return {"status": "ok", "payload": payload, "fabricated": False, **extra}


def _err(exc: Exception) -> dict[str, Any]:
    return {"status": "error", "error": str(exc)[:240], "fabricated": False}


def handle_universe() -> dict[str, Any]:
    try:
        from universe_intelligence.pipeline import run_universe_intelligence_pipeline

        try:
            report = run_universe_intelligence_pipeline(universe_id="NIFTY_500")
        except TypeError:
            report = run_universe_intelligence_pipeline()
        return _ok(report)
    except Exception as exc:
        return _err(exc)


def handle_historical() -> dict[str, Any]:
    # LIDI soft-wire: live collectors → validate → derive → knowledge/packs before KF path.
    # Never silent fixture fallback; recorded samples only via explicit env in non-prod.
    lidi_report: dict[str, Any] | None = None
    try:
        from live_data.production import run_morning_live_ingestion

        lidi_report = run_morning_live_ingestion()
    except Exception as lidi_exc:  # noqa: BLE001
        lidi_report = {
            "ok": False,
            "error": str(lidi_exc)[:240],
            "transparent_insufficiency": True,
            "fixture": False,
        }
        store.alert(
            "warning",
            f"LIDI ingestion unavailable — continuing with transparent insufficiency: {lidi_exc}"[:200],
            workflow_id="historical_update",
        )

    try:
        from knowledge_factory.production import run_daily_pipeline

        # Track-1 + optional HD; IKS layers run as separate workflows
        report = run_daily_pipeline(historical_depth=True, institutional_knowledge=False)
        return _ok(
            report,
            lidi=lidi_report,
            live_data_preferred=True,
            fixture_collectors_disabled_for_lidi=bool((lidi_report or {}).get("ok")),
        )
    except Exception as exc:
        # Soft: try HD alone
        try:
            from knowledge_factory.production import run_historical_depth_pipeline

            return _ok(
                run_historical_depth_pipeline(),
                degraded=True,
                lidi=lidi_report,
                live_data_preferred=True,
            )
        except Exception as exc2:
            if lidi_report and lidi_report.get("ok"):
                return _ok(
                    {"knowledge_factory": "unavailable", "lidi": lidi_report},
                    degraded=True,
                    lidi=lidi_report,
                    live_data_preferred=True,
                )
            return _err(exc2 if str(exc2) else exc)


def handle_company() -> dict[str, Any]:
    idi_report: dict[str, Any] | None = None
    try:
        from knowledge_factory.institutional_documents.production import run_pipeline as run_idi

        # Soft-wire: institutional documents update with company intelligence (evidence only).
        idi_report = run_idi(tickers=["INFY", "TCS", "RELIANCE"], allow_samples=True)
    except Exception as idi_exc:  # noqa: BLE001
        idi_report = {
            "ok": False,
            "error": str(idi_exc)[:200],
            "transparent_insufficiency": True,
            "fabricated": False,
        }
        store.alert(
            "warning",
            f"IDI document ingestion soft-wire unavailable: {idi_exc}"[:200],
            workflow_id="company_intelligence",
        )
    try:
        from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline

        return _ok(run_company_intelligence_pipeline(), idi=idi_report, documents_soft_wire=True)
    except Exception as exc:
        if idi_report and (idi_report.get("ingested_ok") or idi_report.get("status") == "ok"):
            return _ok(
                {"company_intelligence": "unavailable", "idi": idi_report},
                degraded=True,
                idi=idi_report,
                documents_soft_wire=True,
            )
        return _err(exc)


def handle_corporate_events() -> dict[str, Any]:
    lidi_packs = None
    try:
        from live_data import store as lidi_store

        last = lidi_store.get_last_run() or {}
        lidi_packs = (last.get("publish") or {}).get("pack_ids")
    except Exception:
        lidi_packs = None
    try:
        from knowledge_factory.corporate_events.pipeline import run_corporate_events_pipeline

        return _ok(run_corporate_events_pipeline(), lidi_pack_ids=lidi_packs, live_data_preferred=True)
    except Exception as exc:
        if lidi_packs:
            return _ok(
                {"corporate_events": "kf_unavailable", "lidi_pack_ids": lidi_packs},
                degraded=True,
                lidi_pack_ids=lidi_packs,
                live_data_preferred=True,
            )
        return _err(exc)


def handle_government() -> dict[str, Any]:
    try:
        from knowledge_factory.government_intelligence.pipeline import (
            run_government_intelligence_pipeline,
        )

        return _ok(run_government_intelligence_pipeline())
    except Exception as exc:
        return _err(exc)


def handle_industry() -> dict[str, Any]:
    try:
        from knowledge_factory.industry_intelligence.pipeline import (
            run_industry_intelligence_pipeline,
        )

        return _ok(run_industry_intelligence_pipeline())
    except Exception as exc:
        return _err(exc)


def handle_relationships() -> dict[str, Any]:
    try:
        from knowledge_factory.economic_relationship_intelligence.pipeline import (
            run_economic_relationship_pipeline,
        )

        return _ok(run_economic_relationship_pipeline())
    except Exception as exc:
        return _err(exc)


def handle_alternative_data() -> dict[str, Any]:
    try:
        from knowledge_factory.alternative_data_intelligence.pipeline import (
            run_alternative_data_pipeline,
        )

        return _ok(run_alternative_data_pipeline())
    except Exception as exc:
        store.alert("warning", "Alternative data unavailable — continuing", workflow_id="alternative_data")
        return {
            "status": "error",
            "error": str(exc)[:240],
            "dataset_unavailable": True,
            "continue_platform": True,
            "fabricated": False,
        }


def handle_expectations() -> dict[str, Any]:
    try:
        from knowledge_factory.market_expectations_intelligence.pipeline import (
            run_market_expectations_pipeline,
        )

        return _ok(run_market_expectations_pipeline())
    except Exception as exc:
        return _err(exc)


def handle_evidence_packs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Regenerate evidence using Track-1 daily soft path; tolerate missing layers."""
    iere_report: dict[str, Any] | None = None
    try:
        from knowledge_factory.production import run_daily_pipeline

        unavailable = [
            wid
            for wid, st in (ctx.get("completed") or {}).items()
            if st == "error"
        ]
        report = run_daily_pipeline(historical_depth=False, institutional_knowledge=False)
        # Soft-wire IERE — warm ranked institutional evidence packs (never changes KF report).
        try:
            from evidence_retrieval.production import company as iere_company
            from evidence_retrieval.production import health as iere_health

            warmed = []
            for ticker in ("INFY", "TCS", "RELIANCE"):
                out = iere_company(ticker)
                warmed.append(
                    {
                        "ticker": ticker,
                        "retrieval_id": out.get("retrieval_id"),
                        "ranked_count": out.get("ranked_count"),
                        "pack_ids": out.get("pack_ids") or [],
                    }
                )
            iere_report = {
                "ok": True,
                "health": iere_health(),
                "warmed": warmed,
                "fabricated": False,
                "reasoning_changed": False,
            }
        except Exception as iere_exc:  # noqa: BLE001
            iere_report = {
                "ok": False,
                "error": str(iere_exc)[:200],
                "transparent_insufficiency": True,
                "fabricated": False,
            }
            store.alert(
                "warning",
                f"IERE evidence retrieval soft-wire unavailable: {iere_exc}"[:200],
                workflow_id="evidence_pack_generation",
            )
        return _ok(
            report,
            regenerated_without=unavailable,
            transparent_insufficiency=bool(unavailable),
            iere=iere_report,
            evidence_retrieval_soft_wire=True,
        )
    except Exception as exc:
        if iere_report and iere_report.get("ok"):
            return _ok(
                {"knowledge_factory": "unavailable", "iere": iere_report},
                degraded=True,
                iere=iere_report,
                evidence_retrieval_soft_wire=True,
            )
        return _err(exc)


def handle_coverage() -> dict[str, Any]:
    try:
        from knowledge_factory.coverage import morning_coverage_dashboard, decision_coverage

        morning = morning_coverage_dashboard()
        decision = decision_coverage()
        return _ok({"morning": morning, "decision": decision})
    except Exception as exc:
        return _err(exc)


def handle_quality_gates(ctx: dict[str, Any]) -> dict[str, Any]:
    from institutional_scheduler.health.gates import evaluate_morning_gates

    return evaluate_morning_gates(ctx)


def handle_mission_control() -> dict[str, Any]:
    """Queue MC snapshot rebuild (or wait briefly). Never leave HTTP path hanging on aggregate."""
    try:
        from mission_control.production import rebuild
        from mission_control.snapshot import read_dashboard

        queued = rebuild(trigger="institutional_scheduler", wait=False)
        return _ok({"rebuild": queued, "dashboard": read_dashboard()})
    except Exception as exc:
        return _err(exc)


def handle_daily_health() -> dict[str, Any]:
    try:
        from knowledge_factory.coverage import daily_health_scorecard

        base = daily_health_scorecard(ensure_pipeline=False)
    except Exception as exc:
        base = {"unavailable": True, "error": str(exc)[:160]}
    stats = store.workflow_stats()
    retries = sum(int(s.get("failures") or 0) for s in stats.values())
    avg = None
    durs = [s.get("average_runtime_ms") for s in stats.values() if s.get("average_runtime_ms") is not None]
    if durs:
        avg = round(sum(durs) / len(durs), 2)
    board = {
        "title": "AGIB Daily Health",
        "knowledge_factory_daily_health": base,
        "universe_coverage": (base or {}).get("universe") if isinstance(base, dict) else None,
        "knowledge_coverage": (base or {}).get("coverage") if isinstance(base, dict) else None,
        "evidence_coverage": (base or {}).get("evidence") if isinstance(base, dict) else None,
        "historical_coverage": (base or {}).get("historical") if isinstance(base, dict) else None,
        "alternative_data_coverage": (base or {}).get("alternative_data") if isinstance(base, dict) else None,
        "expectation_coverage": (base or {}).get("expectations") if isinstance(base, dict) else None,
        "validation_failures": (base or {}).get("validation_failures") if isinstance(base, dict) else None,
        "collector_failures": (base or {}).get("collector_failures") if isinstance(base, dict) else None,
        "retry_count": retries,
        "scheduler_health": store.get_status(),
        "average_runtime_ms": avg,
        "warnings": [a for a in store.list_alerts(limit=50) if a.get("level") in {"warning", "operator"}],
        "critical_issues": [a for a in store.list_alerts(limit=50) if a.get("level") == "critical"],
        "recommendation": None,
        "knowledge_only": True,
        "fabricated": False,
    }
    return _ok(board)


def handle_research_queue(ctx: dict[str, Any]) -> dict[str, Any]:
    """Knowledge-only research queue — no recommendations."""
    completed = ctx.get("completed") or {}
    queue = []
    for wid, st in completed.items():
        if st == "error":
            queue.append(
                {
                    "item": f"review_failed_workflow:{wid}",
                    "priority": "high",
                    "type": "ops_review",
                    "recommendation": None,
                }
            )
    queue.append(
        {
            "item": "morning_coverage_review",
            "priority": "normal",
            "type": "coverage",
            "recommendation": None,
        }
    )
    queue.append(
        {
            "item": "expectation_changes_review",
            "priority": "normal",
            "type": "expectations",
            "recommendation": None,
        }
    )
    return _ok({"queue": queue, "count": len(queue), "knowledge_only": True})


def handle_morning_reports(ctx: dict[str, Any]) -> dict[str, Any]:
    from institutional_scheduler.reports.morning import generate_morning_reports

    reports = generate_morning_reports(ctx)
    return _ok(reports, report_ids=list(reports.keys()))


def handle_ready(ctx: dict[str, Any]) -> dict[str, Any]:
    gates = (ctx.get("results") or {}).get("quality_gates") or {}
    payload = gates.get("payload") or gates
    passed = bool(payload.get("passed")) if isinstance(payload, dict) else False
    errors = [
        wid for wid, st in (ctx.get("completed") or {}).items() if st == "error"
    ]
    critical_failed = any(
        (ctx.get("completed") or {}).get(w) == "error"
        for w in ("universe_update", "company_intelligence", "evidence_pack_generation", "coverage_validation")
    )
    if passed and not critical_failed:
        state = "READY"
        ready = True
    elif not critical_failed and errors:
        state = "PARTIAL_READY"
        ready = False
    elif critical_failed:
        state = "FAILED"
        ready = False
    else:
        state = "WARNING"
        ready = False
    store.set_status(state=state, system_ready=ready)
    return _ok(
        {
            "state": state,
            "system_ready": ready,
            "gates_passed": passed,
            "errors": errors,
            "critical_failed": critical_failed,
        }
    )


HANDLERS: dict[str, Any] = {
    "universe_update": lambda ctx: handle_universe(),
    "historical_update": lambda ctx: handle_historical(),
    "company_intelligence": lambda ctx: handle_company(),
    "corporate_events": lambda ctx: handle_corporate_events(),
    "government_intelligence": lambda ctx: handle_government(),
    "industry_intelligence": lambda ctx: handle_industry(),
    "economic_relationships": lambda ctx: handle_relationships(),
    "alternative_data": lambda ctx: handle_alternative_data(),
    "market_expectations": lambda ctx: handle_expectations(),
    "evidence_pack_generation": handle_evidence_packs,
    "coverage_validation": lambda ctx: handle_coverage(),
    "quality_gates": handle_quality_gates,
    "mission_control": lambda ctx: handle_mission_control(),
    "daily_health": lambda ctx: handle_daily_health(),
    "research_queue": handle_research_queue,
    "morning_reports": handle_morning_reports,
    "ready_declaration": handle_ready,
}
