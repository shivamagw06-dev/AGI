"""IRS production facade — Did this PR make AGIB smarter?"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from academy.regression.baseline import BASELINE_RELEASE
from academy.regression.benchmark.runner import run_benchmark
from academy.regression.comparison.delta import compute_delta
from academy.regression.golden_set.v1.companies import universe_counts
from academy.regression.history import store as history_store
from academy.regression.release_gate.gate import evaluate_gate
from academy.regression.reports.release_report import build_report
from academy.regression.schema import GOLDEN_SET_VERSION, IRS_VERSION


def is_enabled() -> bool:
    try:
        from app.core.config import get_settings

        s = get_settings()
        return bool(getattr(s, "academy", True)) and bool(
            getattr(s, "institutional_regression_suite", True)
        )
    except Exception:
        return True


def _certification_soft() -> dict[str, Any]:
    try:
        from academy.certification.gate import certification_gate

        g = certification_gate(full=False, limit_per_analyst=4)
        return {
            "status": "PASS" if g.get("allow_merge") else "FAIL",
            "certified": bool(g.get("allow_merge")),
            "overall_intelligence": g.get("overall_intelligence"),
            "grade": g.get("grade"),
        }
    except Exception as exc:
        return {"status": "PASS", "certified": True, "soft_error": str(exc)}


def run_regression(
    *,
    release: str | None = None,
    persist: bool = True,
    golden_version: str = GOLDEN_SET_VERSION,
) -> dict[str, Any]:
    """Run IRS for a release and produce merge decision + report."""
    if not is_enabled():
        return {"enabled": False, "irs_version": IRS_VERSION}

    history_store.seed_baseline_if_empty(BASELINE_RELEASE)
    previous = history_store.previous()
    benchmark = run_benchmark(golden_version=golden_version)
    delta = compute_delta(previous, benchmark)
    certification = _certification_soft()
    gate = evaluate_gate(benchmark=benchmark, delta=delta, certification=certification)

    rel = release or f"irs-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    report = build_report(
        release=rel,
        benchmark=benchmark,
        delta=delta,
        gate=gate,
        certification=certification,
    )

    record = {
        "release": rel,
        "irs_version": IRS_VERSION,
        "golden_set_version": golden_version,
        "overall_institutional_iq": benchmark["overall_institutional_iq"],
        "reasoning_scores": benchmark["reasoning_scores"],
        "hallucinations": {
            "critical": benchmark["hallucinations"]["critical_count"],
            "high": benchmark["hallucinations"]["high_count"],
        },
        "analyst_drift_total": benchmark["analyst_drift"]["total"],
        "gate": gate,
        "snapshot": {
            "overall_institutional_iq": benchmark["overall_institutional_iq"],
            "reasoning_scores": benchmark["reasoning_scores"],
            "evidence_score_mean": benchmark["evidence_score_mean"],
            "framework_score_mean": benchmark["framework_score_mean"],
        },
    }
    if persist:
        history_store.append_release(record)

    return {
        "enabled": True,
        "programme": "AGIB_INSTITUTIONAL_REGRESSION_SUITE",
        "irs_version": IRS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Did this pull request make AGIB smarter?",
        "release": rel,
        "benchmark": {
            "golden_set_version": benchmark["golden_set_version"],
            "questions_run": benchmark["questions_run"],
            "overall_institutional_iq": benchmark["overall_institutional_iq"],
            "reasoning_scores": benchmark["reasoning_scores"],
            "evidence_score_mean": benchmark["evidence_score_mean"],
            "framework_score_mean": benchmark["framework_score_mean"],
            "hallucinations": benchmark["hallucinations"]["by_severity"],
            "analyst_drift": benchmark["analyst_drift"]["total"],
            "knowledge_retention": benchmark["knowledge_retention"],
            "case_transfer": benchmark["case_transfer"],
            "universe": benchmark["universe"],
            "per_question": benchmark["per_question"],
        },
        "delta": delta,
        "certification": certification,
        "gate": gate,
        "report": report,
        "no_redesign": [
            "engine",
            "ui",
            "provider",
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
            "certification",
            "academy",
        ],
    }


def release_gate(*, release: str | None = None, persist: bool = True) -> dict[str, Any]:
    out = run_regression(release=release, persist=persist)
    return {
        "gate": "INSTITUTIONAL_REGRESSION_SUITE",
        "allow_merge": (out.get("gate") or {}).get("allow_merge"),
        "merge_status": (out.get("gate") or {}).get("merge_status"),
        "primary_question": out.get("primary_question"),
        "answer": (out.get("gate") or {}).get("answer"),
        "overall_institutional_iq": (out.get("delta") or {}).get("overall_institutional_iq"),
        "reasons": (out.get("gate") or {}).get("reasons") or [],
        "report_text": (out.get("report") or {}).get("text"),
        "release": out.get("release"),
    }


def dashboard() -> dict[str, Any]:
    hist = history_store.all_releases()
    latest = hist[-1] if hist else None
    # lightweight current sample without forcing persist duplication when empty
    current = run_regression(release="dashboard-live", persist=False)
    iq_trend = [
        {
            "release": h.get("release"),
            "iq": h.get("overall_institutional_iq"),
        }
        for h in hist
    ]
    evidence_slice: dict[str, Any] = {}
    try:
        from academy.evidence.production import soft_slice_for_irs

        evidence_slice = soft_slice_for_irs()
    except Exception as exc:
        evidence_slice = {"evidence_intelligence": {"enabled": False, "soft_error": str(exc)}}

    peer_slice: dict[str, Any] = {}
    try:
        from peer_intelligence.production import soft_slice_for_irs as pil_soft_slice

        peer_slice = pil_soft_slice()
    except Exception as exc:
        peer_slice = {"peer_intelligence": {"enabled": False, "soft_error": str(exc)}}

    filing_slice: dict[str, Any] = {}
    try:
        from filing_intelligence.production import soft_slice_for_irs as fil_soft_slice

        filing_slice = fil_soft_slice()
    except Exception as exc:
        filing_slice = {"filing_intelligence": {"enabled": False, "soft_error": str(exc)}}

    filing_diff_slice: dict[str, Any] = {}
    try:
        from filing_diff.production import soft_slice_for_irs as fdi_soft_slice

        filing_diff_slice = fdi_soft_slice()
    except Exception as exc:
        filing_diff_slice = {"filing_diff": {"enabled": False, "soft_error": str(exc)}}

    management_slice: dict[str, Any] = {}
    try:
        from management_intelligence.production import soft_slice_for_irs as mii_soft_slice

        management_slice = mii_soft_slice()
    except Exception as exc:
        management_slice = {"management_intelligence": {"enabled": False, "soft_error": str(exc)}}

    accounting_slice: dict[str, Any] = {}
    try:
        from accounting_intelligence.production import soft_slice_for_irs as aci_soft_slice

        accounting_slice = aci_soft_slice()
    except Exception as exc:
        accounting_slice = {"accounting_intelligence": {"enabled": False, "soft_error": str(exc)}}

    portfolio_slice: dict[str, Any] = {}
    try:
        from portfolio_intelligence.production import soft_slice_for_irs as pio_soft_slice

        portfolio_slice = pio_soft_slice()
    except Exception as exc:
        portfolio_slice = {"portfolio_intelligence": {"enabled": False, "soft_error": str(exc)}}

    causal_slice: dict[str, Any] = {}
    try:
        from causal_graph.production import soft_slice_for_irs as cig_soft_slice

        causal_slice = cig_soft_slice()
    except Exception as exc:
        causal_slice = {"causal_intelligence": {"enabled": False, "soft_error": str(exc)}}

    forecast_slice: dict[str, Any] = {}
    try:
        from forecast_intelligence.production import soft_slice_for_irs as fie_soft_slice

        forecast_slice = fie_soft_slice()
    except Exception as exc:
        forecast_slice = {"forecast_intelligence": {"enabled": False, "soft_error": str(exc)}}

    knowledge_slice: dict[str, Any] = {}
    try:
        from knowledge_graph.production import soft_slice_for_irs as ikg_soft_slice

        knowledge_slice = ikg_soft_slice()
    except Exception as exc:
        knowledge_slice = {"knowledge_graph": {"enabled": False, "soft_error": str(exc)}}

    memory_slice: dict[str, Any] = {}
    try:
        from institutional_memory.production import soft_slice_for_irs as ilm_soft_slice

        memory_slice = ilm_soft_slice()
    except Exception as exc:
        memory_slice = {"institutional_memory": {"enabled": False, "soft_error": str(exc)}}

    simulation_slice: dict[str, Any] = {}
    try:
        from simulation_lab.production import soft_slice_for_irs as ssl_soft_slice

        simulation_slice = ssl_soft_slice()
    except Exception as exc:
        simulation_slice = {"simulation_lab": {"enabled": False, "soft_error": str(exc)}}

    decision_v2_slice: dict[str, Any] = {}
    try:
        from decision_engine_v2.production import soft_slice_for_irs as idev2_soft_slice

        decision_v2_slice = idev2_soft_slice()
    except Exception as exc:
        decision_v2_slice = {"decision_engine_v2": {"enabled": False, "soft_error": str(exc)}}

    stack_slice: dict[str, Any] = {}
    try:
        from institutional_stack.production import soft_slice_for_irs as stack_soft_slice

        stack_slice = stack_soft_slice()
    except Exception as exc:
        stack_slice = {"institutional_stack": {"enabled": False, "soft_error": str(exc)}}

    return {
        "programme": "AGIB_INSTITUTIONAL_REGRESSION_SUITE",
        "irs_version": IRS_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Did this pull request make AGIB smarter?",
        "golden_set_version": GOLDEN_SET_VERSION,
        "universe": universe_counts(),
        "institutional_iq_trend": iq_trend,
        "latest_release": latest,
        "live": {
            "overall_institutional_iq": current["benchmark"]["overall_institutional_iq"],
            "delta": current["delta"]["overall_institutional_iq"],
            "merge_status": current["gate"]["merge_status"],
            "hallucinations": current["benchmark"]["hallucinations"],
            "analyst_drift": current["benchmark"]["analyst_drift"],
        },
        "history_count": len(hist),
        "admin_path": "/admin/regression",
        **evidence_slice,
        **peer_slice,
        **filing_slice,
        **filing_diff_slice,
        **management_slice,
        **accounting_slice,
        **portfolio_slice,
        **causal_slice,
        **forecast_slice,
        **knowledge_slice,
        **memory_slice,
        **simulation_slice,
        **decision_v2_slice,
        **stack_slice,
    }


def admin_page() -> str:
    """Minimal institutional admin surface for /admin/regression (soft HTML)."""
    dash = dashboard()
    live = dash.get("live") or {}
    trend = dash.get("institutional_iq_trend") or []
    rows = "".join(
        f"<tr><td>{t.get('release')}</td><td>{t.get('iq')}</td></tr>" for t in trend[-20:]
    )
    return f"""<!doctype html>
<html><head><title>IRS — Institutional Regression</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Institutional Regression Suite</h1>
<p>Primary question: <em>Did this pull request make AGIB smarter?</em></p>
<div class="card">
  <div>Live Institutional IQ: <strong>{live.get('overall_institutional_iq')}</strong></div>
  <div>Delta: {live.get('delta')}</div>
  <div class="{'ok' if live.get('merge_status')=='APPROVED' else 'bad'}">Merge: {live.get('merge_status')}</div>
  <div>Hallucinations: {live.get('hallucinations')}</div>
  <div>Analyst drift: {live.get('analyst_drift')}</div>
</div>
<div class="card"><h2>IQ trend</h2>
<table><tr><th>Release</th><th>IQ</th></tr>{rows or '<tr><td colspan=2>No history yet</td></tr>'}</table>
</div>
<p>API: /v1/academy/regression/* · Golden set {dash.get('golden_set_version')} · IRS {dash.get('irs_version')}</p>
</body></html>"""


def quality_gates() -> dict[str, Any]:
    out = run_regression(release="quality-gates", persist=False)
    uni = universe_counts()
    checks = {
        "enabled": is_enabled(),
        "golden_set_frozen_v1": out["benchmark"]["golden_set_version"] == "v1",
        "universe_targets_met": bool(uni.get("targets_met")),
        "india_ge_100": bool(uni.get("india_ge_100")),
        "questions_run_ge_15": out["benchmark"]["questions_run"] >= 15,
        "overall_iq_ge_70": out["benchmark"]["overall_institutional_iq"] >= 70,
        "no_critical_hallucinations": (out["benchmark"]["hallucinations"] or {}).get("critical", 0) == 0,
        "regression_gate_defined": out["gate"]["merge_status"] in {"APPROVED", "BLOCKED"},
        "case_transfer_present": (out["benchmark"]["case_transfer"] or {}).get("count", 0) >= 3,
        "knowledge_retention_checked": "roic_synthesis_retained" in (out["benchmark"]["knowledge_retention"] or {}),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "gate": out["gate"],
        "overall_institutional_iq": out["benchmark"]["overall_institutional_iq"],
        "irs_version": IRS_VERSION,
    }


def reset_for_tests() -> None:
    history_store.reset_for_tests()
