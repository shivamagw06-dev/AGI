"""IEL benchmark runner — GitHub commit → questions → AGIB → judge → score."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any
from uuid import uuid4

from institutional_evaluation_lab.analytics.root_cause import cluster_failures
from institutional_evaluation_lab.benchmarks.probe import probe_question
from institutional_evaluation_lab.datasets.catalog import load_suite
from institutional_evaluation_lab.judges.structural import judge_all
from institutional_evaluation_lab.regression.compare import compare_to_baseline
from institutional_evaluation_lab.schema import IEL_VERSION, MODULE_CODE, QUALITY_TARGETS
from institutional_evaluation_lab.scoring.engine import aggregate_suite, score_question
from institutional_evaluation_lab import store


def _git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.environ.get("IEL_GIT_ROOT", "/workspace"),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return None


def run_benchmark(
    *,
    suite: str = "smoke",
    mode: str = "soft",
    limit: int | None = None,
    persist_baseline: bool = False,
    compare_baseline: bool = True,
) -> dict[str, Any]:
    """
    Run IEL suite.

    suite: cio_frozen_25 | investor_100 | institutional_1000 | smoke | all
    mode: soft (nightly default) | full (sample)
    """
    t0 = time.time()
    if suite in {"phase1_golden_200", "phase1_golden"}:
        from institutional_evaluation_lab.datasets.phase1_golden_universe import universe_board

        board = universe_board()
        return {
            "module": MODULE_CODE,
            "version": IEL_VERSION,
            "suite": "phase1_golden_200",
            "kind": "universe",
            "mode": mode,
            "n": board.get("n"),
            "valid": board.get("valid"),
            "summary": board.get("summary"),
            "buckets": board.get("buckets"),
            "elapsed_ms": int((time.time() - t0) * 1000),
            "note": "Phase 1 golden set is a company universe, not a question suite.",
            "fabricated": False,
        }

    questions = load_suite(suite)
    if limit is not None:
        questions = questions[: max(1, int(limit))]

    scored: list[dict[str, Any]] = []
    for q in questions:
        try:
            probe = probe_question(q, mode=mode)
            judgments = judge_all(q, probe)
            row = score_question(q, judgments)
            row["probe_mode"] = probe.get("mode")
            row["intent_observed"] = (probe.get("intent_resolution") or {}).get("intent")
            row["actual_intent"] = (probe.get("intent_resolution") or {}).get("intent")
            row["playbook_id"] = (probe.get("playbook_selection") or {}).get("playbook_id")
            row["actual_playbook"] = (probe.get("playbook_selection") or {}).get("playbook_id")
            row["framework_ids"] = (probe.get("framework_selection") or {}).get("framework_ids")
            row["actual_framework"] = list(
                (probe.get("framework_selection") or {}).get("framework_ids") or []
            )
            row["imai_hit"] = (probe.get("institutional_memory") or {}).get("have_we_seen_this_before")
            row["ieg_nodes"] = (probe.get("evidence_graph") or {}).get("n_nodes")
            row["evidence_present"] = {
                "n_nodes": (probe.get("evidence_graph") or {}).get("n_nodes"),
                "entities": (probe.get("evidence_graph") or {}).get("entities"),
                "domain_coverage_pct": (probe.get("evidence_graph") or {}).get("domain_coverage_pct"),
                "surface_bullets": ((probe.get("evidence_graph") or {}).get("surface_bullets") or [])[:4],
            }
            row["reasoning_path"] = {
                "governance_path": ((probe.get("governance") or {}).get("path")),
                "mode": probe.get("mode"),
                "reasoning_changed": probe.get("reasoning_changed"),
            }
            row["communication"] = {
                "template": (probe.get("communication") or {}).get("template"),
                "institutional_memory_visible": (probe.get("communication") or {}).get(
                    "institutional_memory_visible"
                ),
            }
            scored.append(row)
        except Exception as exc:
            scored.append(
                {
                    "question_id": q.get("question_id"),
                    "category": q.get("category"),
                    "difficulty": q.get("difficulty"),
                    "suite": q.get("suite"),
                    "overall": 0.0,
                    "passed": False,
                    "verdict": "FAIL",
                    "root_causes": [f"probe_error:{str(exc)[:120]}"],
                    "dimensions": {},
                    "error": str(exc)[:240],
                }
            )

    agg = aggregate_suite(scored)
    # Phase 4/5 — HQS / CQS / CFQS / ITQS / DQS / PQS / MQS / LQS (independent of CIO)
    from institutional_evaluation_lab.judges.committee_quality import aggregate_cqs
    from institutional_evaluation_lab.judges.confidence_quality import aggregate_cfqs
    from institutional_evaluation_lab.judges.decision_quality import aggregate_dqs
    from institutional_evaluation_lab.judges.hypothesis_quality import aggregate_hqs
    from institutional_evaluation_lab.judges.learning_quality import aggregate_lqs
    from institutional_evaluation_lab.judges.monitoring_quality import aggregate_mqs
    from institutional_evaluation_lab.judges.portfolio_quality import aggregate_pqs
    from institutional_evaluation_lab.judges.thesis_quality import aggregate_itqs

    hqs_summary = aggregate_hqs(scored)
    cqs_summary = aggregate_cqs(scored)
    cfqs_summary = aggregate_cfqs(scored)
    itqs_summary = aggregate_itqs(scored)
    dqs_summary = aggregate_dqs(scored)
    pqs_summary = aggregate_pqs(scored)
    mqs_summary = aggregate_mqs(scored)
    lqs_summary = aggregate_lqs(scored)
    agg["hypothesis_quality"] = hqs_summary
    agg["committee_quality"] = cqs_summary
    agg["confidence_quality"] = cfqs_summary
    agg["thesis_quality"] = itqs_summary
    agg["decision_quality"] = dqs_summary
    agg["portfolio_quality"] = pqs_summary
    agg["monitoring_quality"] = mqs_summary
    agg["learning_quality"] = lqs_summary
    clusters = cluster_failures(scored)
    run_id = f"iel-run-{uuid4().hex[:10]}"
    commit = _git_commit()
    baseline = store.load_baseline() if compare_baseline else None
    regression = compare_to_baseline(agg, baseline)

    # Distance to quality targets
    targets = {
        "benchmark_1000_pass_pct": {
            "target": QUALITY_TARGETS["benchmark_1000_pass_pct"],
            "observed": agg["pass_pct"] if suite in {"institutional_1000", "all", "smoke"} else None,
            "gap": (
                round(QUALITY_TARGETS["benchmark_1000_pass_pct"] - agg["pass_pct"], 2)
                if suite in {"institutional_1000", "all", "smoke"}
                else None
            ),
        },
        "framework_selection_proxy": {
            "target": QUALITY_TARGETS["framework_selection_pct"],
            "note": "Proxy = share of questions with framework dimension passed",
        },
    }
    fw_pass = sum(
        1
        for r in scored
        if ((r.get("dimensions") or {}).get("framework") or {}).get("passed")
    )
    targets["framework_selection_proxy"]["observed"] = round(100.0 * fw_pass / max(1, len(scored)), 2)

    summary = {
        "run_id": run_id,
        "module": MODULE_CODE,
        "iel_version": IEL_VERSION,
        "suite": suite,
        "mode": mode,
        "commit": commit,
        "n_questions": len(questions),
        "aggregate": agg,
        "hypothesis_quality_score": hqs_summary,
        "committee_quality_score": cqs_summary,
        "confidence_quality_score": cfqs_summary,
        "thesis_quality_score": itqs_summary,
        "decision_quality_score": dqs_summary,
        "portfolio_quality_score": pqs_summary,
        "monitoring_quality_score": mqs_summary,
        "learning_quality_score": lqs_summary,
        "failure_clusters": clusters,
        "regression": regression,
        "targets": targets,
        "latency_ms": int((time.time() - t0) * 1000),
        "reasoning_changed": False,
        "fabricated": False,
        "rows": scored,
    }
    # Soft-wire RCI (Sprint 3.2) — engineering brain; does not change product reasoning
    try:
        from root_cause_intelligence.analyze import analyze_iel_run

        rci = analyze_iel_run(summary, persist=True)
        summary["root_cause_intelligence"] = {
            "analysis_id": rci.get("analysis_id"),
            "n_failures": rci.get("n_failures"),
            "n_clusters": rci.get("n_clusters"),
            "top_10_clusters": rci.get("top_10_clusters"),
            "recommended_prs": rci.get("recommended_prs"),
            "kpi_proxies": rci.get("kpi_proxies"),
            "gaps": rci.get("gaps"),
            "version": rci.get("version"),
        }
    except Exception as exc:
        summary["root_cause_intelligence"] = {
            "status": "error",
            "error": str(exc)[:200],
        }
    store.record_run(summary)
    if persist_baseline or (baseline is None and suite in {"institutional_1000", "cio_frozen_25", "smoke"}):
        # Auto-establish baseline on first meaningful run; explicit flag overwrites
        if persist_baseline or baseline is None:
            store.save_baseline(summary)
            summary["baseline_saved"] = True
    return summary
