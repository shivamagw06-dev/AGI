"""Production façade for Institutional Evaluation Lab (IEL)."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.benchmarks.runner import run_benchmark
from institutional_evaluation_lab.dashboards.board import build_board
from institutional_evaluation_lab.datasets.catalog import catalog_stats, get_question, load_suite
from institutional_evaluation_lab.reports.builder import build_markdown_report
from institutional_evaluation_lab.schema import FREEZE_LOCKS, IEL_VERSION, MODULE_CODE, PROGRAMME, QUALITY_TARGETS
from institutional_evaluation_lab import store


def status() -> dict[str, Any]:
    stats = catalog_stats()
    golden = None
    try:
        from institutional_evaluation_lab.golden_universe.runner import health as golden_health

        golden = golden_health()
    except Exception:
        golden = {"status": "unavailable"}
    return {
        "module": MODULE_CODE,
        "version": IEL_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "catalogue": stats,
        "golden_universe_evaluation": golden,
        "governance_spec": {
            "active": "v1.0",
            "frozen": True,
            "phase6": "execute GOV-001…GOV-008 against results/{release}/*.json",
        },
        "recommendation_drift": {
            "version": "recommendation-drift-v1.0.0",
            "reason_codes": ["DATA", "MARKET", "MODEL", "GOVERNANCE", "BUGFIX", "UNKNOWN"],
            "unknown_is_regression": True,
        },
        "release_observability": {
            "version": "release-observability-v1.0.0",
            "presentation_only": True,
            "consumes": ["evaluation_lab", "phase6_governance", "recommendation_drift"],
        },
        "institutional_acceptance_test": {
            "version": "institutional-acceptance-test-v1.0.0",
            "question": "Is AGIB ready to become the baseline architecture?",
            "universe_n": 200,
            "acceptance_exam_only": True,
        },
        "quality_targets": QUALITY_TARGETS,
        "freeze_locks": dict(FREEZE_LOCKS),
        "nightly_default": {"suite": "institutional_1000", "mode": "soft"},
        "api_prefix": "/v1/institutional-evaluation-lab",
        "fabricated": False,
    }


def board() -> dict[str, Any]:
    return build_board()


def catalog(*, suite: str = "institutional_1000", limit: int = 50) -> dict[str, Any]:
    if suite in {"phase1_golden_200", "phase1_golden"}:
        from institutional_evaluation_lab.datasets.phase1_golden_universe import universe_board

        board = universe_board()
        rows = load_suite(suite)[: max(1, min(int(limit), 200))]
        return {
            "suite": "phase1_golden_200",
            "kind": "universe",
            "n": board.get("n"),
            "companies": rows,
            "board": board,
            "stats": catalog_stats(),
        }
    rows = load_suite(suite)[: max(1, min(int(limit), 200))]
    return {"suite": suite, "n": len(rows), "questions": rows, "stats": catalog_stats()}


def phase1_golden_universe() -> dict[str, Any]:
    from institutional_evaluation_lab.datasets.phase1_golden_universe import universe_board

    return universe_board()


def golden_evaluation_health() -> dict[str, Any]:
    from institutional_evaluation_lab.golden_universe.runner import health

    return health()


def cre_investment_benchmark() -> dict[str, Any]:
    """Coverage audit for every canonical industry model."""
    from institutional_evaluation_lab.judges.economic_reasoning import evaluate_industry_models
    from institutional_evaluation_lab.datasets.catalog import load_suite
    result = evaluate_industry_models()
    return {"suite": "cre_investment_144", "question_count": len(load_suite("cre_investment_144")),
            "registry_claimed_count": 36, **result, "fabricated": False}


def run_golden_evaluation(
    *,
    limit: int | None = None,
    bucket: str | None = None,
    force_price_refresh: bool = False,
    persist: bool = True,
    persist_baseline: bool = False,
    compare_previous: bool = True,
    release_id: str | None = None,
) -> dict[str, Any]:
    """Evaluation Runner — full institutional pipeline over Phase 1 golden universe."""
    from institutional_evaluation_lab.golden_universe.runner import run_golden_evaluation as _run

    return _run(
        limit=limit,
        bucket=bucket,
        force_price_refresh=force_price_refresh,
        persist=persist,
        persist_baseline=persist_baseline,
        compare_previous=compare_previous,
        release_id=release_id,
    )


def golden_scorecard() -> dict[str, Any]:
    from institutional_evaluation_lab.golden_universe import store as golden_store

    latest = golden_store.load_latest()
    if not latest:
        return {"found": False, "note": "No golden evaluation run yet."}
    return {
        "found": True,
        "scorecard": latest.get("scorecard"),
        "coverage": latest.get("coverage"),
        "run_id": latest.get("run_id"),
        "release_id": latest.get("release_id"),
    }


def golden_drift_report() -> dict[str, Any]:
    from institutional_evaluation_lab.golden_universe import store as golden_store
    from institutional_evaluation_lab.golden_universe.recommendation_drift import (
        compare_recommendation_drift,
    )

    latest = golden_store.load_latest()
    baseline = golden_store.load_baseline()
    if not latest:
        return {"found": False, "note": "No latest golden run."}
    drift = compare_recommendation_drift(
        latest.get("rows") or [],
        (baseline or {}).get("rows") if baseline else None,
        previous_label=str((baseline or {}).get("release_id") or "previous"),
        current_label=str(latest.get("release_id") or "current"),
    )
    return {"found": True, "drift": drift, "baseline_run_id": (baseline or {}).get("run_id")}


def golden_list_releases() -> dict[str, Any]:
    from institutional_evaluation_lab.golden_universe import store as golden_store

    return {
        "results_root": str(golden_store.results_root()),
        "releases": golden_store.list_releases(),
        "layout": "results/{release_id}/{TICKER}.json",
    }


def golden_load_release(release_id: str) -> dict[str, Any]:
    from institutional_evaluation_lab.golden_universe import store as golden_store

    packed = golden_store.load_release_results(release_id)
    if not packed:
        return {"found": False, "release_id": release_id}
    return {
        "found": True,
        "release_id": packed.get("release_id"),
        "results_dir": packed.get("results_dir"),
        "n": packed.get("n"),
        "manifest": packed.get("manifest"),
        "summary": packed.get("summary"),
        "rows_sample": (packed.get("rows") or [])[:20],
    }


def golden_replay(*, release_id: str, ticker: str | None = None, limit: int | None = None) -> dict[str, Any]:
    from institutional_evaluation_lab.replay.engine import replay_release, replay_ticker

    if ticker:
        return replay_ticker(release_id=release_id, ticker=ticker)
    return replay_release(release_id=release_id, limit=limit)


def phase6_governance(
    *,
    release_id: str,
    spec_version: str | None = "v1.0",
    limit: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Phase 6 — execute frozen Governance Spec against Evaluation Lab JSON results."""
    from governance_spec.phase6 import run_phase6
    from institutional_evaluation_lab.golden_universe import store as golden_store

    report = run_phase6(release_id=release_id, spec_version=spec_version, limit=limit)
    if persist and not report.get("error"):
        try:
            import json
            from pathlib import Path

            out_dir = Path(golden_store.release_dir(release_id))
            out_dir.mkdir(parents=True, exist_ok=True)
            light = {k: v for k, v in report.items() if k != "ticker_results"}
            (out_dir / "_phase6_governance.json").write_text(
                json.dumps(light, indent=2, default=str), encoding="utf-8"
            )
            report["report_path"] = str(out_dir / "_phase6_governance.json")
        except Exception as exc:
            report["persist_error"] = str(exc)[:160]
    return report


def recommendation_drift(
    *,
    previous_release: str,
    current_release: str,
    governance_failures: int | None = None,
    persist: bool = True,
    hints: dict[str, str] | None = None,
) -> dict[str, Any]:
    """PR #308 — controlled, explainable recommendation drift across releases."""
    from institutional_evaluation_lab.drift.production import compare_releases

    return compare_releases(
        previous_release=previous_release,
        current_release=current_release,
        governance_failures=governance_failures,
        persist=persist,
        hints=hints,
    )


def release_observability(
    *,
    release_id: str,
    previous_releases: list[str] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """PR #309 — pure observability dashboards over #306–#308 artifacts."""
    from institutional_evaluation_lab.observability.production import build_release_dashboard

    return build_release_dashboard(
        release_id,
        previous_releases=previous_releases,
        persist=persist,
    )


def institutional_acceptance_test(
    *,
    release_id: str,
    previous_release: str | None = None,
    persist: bool = True,
    freeze: bool = False,
    require_full_universe: bool = True,
) -> dict[str, Any]:
    """Phase 1 IAT — final exam for baseline architecture qualification."""
    from institutional_evaluation_lab.iat.production import run_iat

    return run_iat(
        release_id=release_id,
        previous_release=previous_release,
        persist=persist,
        freeze=freeze,
        require_full_universe=require_full_universe,
    )


def question(question_id: str) -> dict[str, Any] | None:
    return get_question(question_id)


def run(
    *,
    suite: str = "smoke",
    mode: str = "soft",
    limit: int | None = None,
    persist_baseline: bool = False,
) -> dict[str, Any]:
    return run_benchmark(
        suite=suite,
        mode=mode,
        limit=limit,
        persist_baseline=persist_baseline,
    )


def nightly() -> dict[str, Any]:
    """Nightly evaluation entry — soft probe over institutional_1000."""
    summary = run_benchmark(
        suite="institutional_1000",
        mode="soft",
        limit=None,
        persist_baseline=False,
        compare_baseline=True,
    )
    report_md = build_markdown_report(summary)
    # Persist report artifact next to baseline
    from pathlib import Path

    out = Path(__file__).resolve().parent / "reports" / "latest_nightly.md"
    out.write_text(report_md, encoding="utf-8")
    # Strip heavy rows for API response
    light = {k: v for k, v in summary.items() if k != "rows"}
    light["report_path"] = str(out)
    light["report_preview"] = report_md[:2000]
    return light


def history(*, limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "rows": store.list_runs(limit=limit), "fabricated": False}


def report(run_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    if run_summary is None:
        runs = store.list_runs(limit=1)
        run_summary = runs[0] if runs else {"aggregate": {}, "suite": None}
    md = build_markdown_report(run_summary)
    return {"markdown": md, "run_id": run_summary.get("run_id"), "fabricated": False}
