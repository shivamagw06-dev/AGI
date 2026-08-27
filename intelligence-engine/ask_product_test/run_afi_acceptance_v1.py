#!/usr/bin/env python3
"""AGI Financial Intelligence Acceptance Test v1.0 — live release gate.

Runs all 40 questions against LIVE Ask (POST /api/ui/search), scores each
against the 6-dimension rubric, computes the required suite metrics, and
writes:

    artifacts/afi_acceptance_v1.json          full report (partial written
                                               after every question so a hang
                                               doesn't lose progress)

Release PASS requires (per spec):
    Overall Score >= 95%, Financial Routing Accuracy = 100%,
    Financial Engine Utilization >= 95%, Generic Retrieval Pollution = 0%,
    Hallucinations = 0, Recommendation Policy = 100%,
    Unknown Entity Handling = 100%, executive answers first every time.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import urllib.request

from ask_product_test import checks
from ask_product_test.afi_acceptance_v1 import AFI_ACCEPTANCE_40, SECTIONS, score_afi_answer
from ask_product_test.harness import AskProductHarness, _artifacts_dir, mirror_artifact_dirs, write_artifact


def _deployment_info(base_url: str) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/health", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return {"commit": data.get("commit"), "environment": base_url, "raw": data}
    except Exception as exc:  # noqa: BLE001
        return {"commit": None, "environment": base_url, "error": str(exc)}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _evaluate_one(case: Dict[str, Any], payload: Dict[str, Any], *, latency_ms: int, http_status: int) -> Dict[str, Any]:
    text = checks.extract_answer_text(payload) if isinstance(payload, dict) else ""
    evidence_n = checks.evidence_count(payload) if isinstance(payload, dict) else 0
    entities_blob = checks.flatten_text(checks.extract_entities(payload)) + " " + checks.flatten_text(payload.get("related_companies")) if isinstance(payload, dict) else ""
    engine_blob = checks.flatten_text(payload) if isinstance(payload, dict) else ""
    # extract_orchestration() normalizes fields present since before the
    # Financial Router; read financial_router_triggered/financial_engine
    # straight off the raw payload since extract_orchestration() predates them.
    raw_orch = payload.get("ask_orchestration") if isinstance(payload, dict) else None
    orch = checks.extract_orchestration(payload) if isinstance(payload, dict) else {}
    if isinstance(raw_orch, dict):
        orch["financial_router_triggered"] = raw_orch.get("financial_router_triggered")
        orch["financial_engine"] = raw_orch.get("financial_engine")
        orch["financial_engine_key"] = raw_orch.get("financial_engine_key")
        orch["short_circuit"] = raw_orch.get("short_circuit")
    degraded = checks.is_degraded(payload) if isinstance(payload, dict) else True
    evidence_sources = checks.evidence_sources(payload) if isinstance(payload, dict) else []
    return score_afi_answer(
        case,
        text=text,
        evidence_count=evidence_n,
        entities_blob=entities_blob,
        engine_blob=engine_blob,
        orch=orch,
        latency_ms=latency_ms,
        http_status=http_status,
        degraded=degraded,
        evidence_sources=evidence_sources,
    )


def _percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = (len(s) - 1) * pct
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return int(s[f] + (s[c] - s[f]) * (k - f))


BASELINE = {
    "overall_score_pct": 53.17,
    "financial_routing_accuracy_pct": 0.0,
    "financial_engine_utilization_pct": 0.0,
    "generic_retrieval_pollution_pct": 100.0,
    "recorded_at": "2026-08-01 (main @ 70cf10d3, pre financial-router)",
}


def _compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows) or 1
    engine_required = [r for r in rows if r.get("requires_engine")]
    engine_hit = [r for r in engine_required if r.get("engine_signal_found")]
    financial_routing_accuracy = round(100.0 * len(engine_hit) / len(engine_required), 2) if engine_required else 100.0
    generic_pollution = round(100.0 * (len(engine_required) - len(engine_hit)) / len(engine_required), 2) if engine_required else 0.0

    policy_rows = [r for r in rows if r["id"] in ("E37", "E38")]
    policy_ok = sum(1 for r in policy_rows if not r["auto_fail_flags"].get("recommendation_policy_regression"))
    recommendation_policy_accuracy = round(100.0 * policy_ok / len(policy_rows), 2) if policy_rows else 100.0

    unknown_rows = [r for r in rows if r["id"] == "E39"]
    unknown_ok = sum(1 for r in unknown_rows if not r["auto_fail_flags"].get("hallucinated_entity"))
    unknown_entity_accuracy = round(100.0 * unknown_ok / len(unknown_rows), 2) if unknown_rows else 100.0

    hallucination_count = sum(
        1 for r in rows if r["auto_fail_flags"].get("hallucinated_entity") or r["auto_fail_flags"].get("wrong_company_injected")
    )
    exec_first_count = sum(1 for r in rows if not r["auto_fail_flags"].get("executive_did_not_answer_first"))
    exec_first_pct = round(100.0 * exec_first_count / total, 2)

    latencies = [r["latency_ms"] for r in rows if isinstance(r.get("latency_ms"), (int, float))]
    total_score = sum(r["final_score"] for r in rows)
    max_score = sum(r["max_score"] for r in rows)
    overall_pct = round(100.0 * total_score / max_score, 2) if max_score else 0.0

    exec_quality_avg = round(sum(r["dimension_scores"]["executive_quality"] for r in rows) / total, 2)

    entity_misfire_count = sum(1 for r in rows if r.get("entity_misfire"))
    # "Executive Composer Success" — the visible answer led with a direct,
    # non-scaffold response (no framework leak, executive answered first).
    exec_success_count = sum(
        1 for r in rows
        if not r["auto_fail_flags"].get("framework_meta_leak")
        and not r["auto_fail_flags"].get("executive_did_not_answer_first")
    )
    executive_composer_success_pct = round(100.0 * exec_success_count / total, 2)
    average_latency_ms = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

    by_section: Dict[str, Any] = {}
    for section in SECTIONS:
        srows = [r for r in rows if r["section"] == section]
        if not srows:
            continue
        by_section[section] = {
            "count": len(srows),
            "avg_score": round(sum(r["final_score"] for r in srows) / len(srows), 2),
            "avg_pct": round(100.0 * sum(r["final_score"] for r in srows) / (30 * len(srows)), 2),
        }

    metrics = {
        "overall_score_pct": overall_pct,
        "total_score": total_score,
        "max_score": max_score,
        "financial_routing_accuracy_pct": financial_routing_accuracy,
        "financial_engine_utilization_pct": financial_routing_accuracy,
        "generic_retrieval_pollution_pct": generic_pollution,
        "entity_misfire_count": entity_misfire_count,
        "executive_composer_success_pct": executive_composer_success_pct,
        "executive_composer_quality_avg": exec_quality_avg,
        "hallucination_count": hallucination_count,
        "recommendation_policy_accuracy_pct": recommendation_policy_accuracy,
        "unknown_entity_accuracy_pct": unknown_entity_accuracy,
        "executive_answers_first_pct": exec_first_pct,
        "latency_ms_p50": _percentile(latencies, 0.50),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "average_latency_ms": average_latency_ms,
        "by_section": by_section,
        "engine_required_questions": len(engine_required),
        "engine_signal_found_count": len(engine_hit),
    }
    metrics["baseline"] = BASELINE
    metrics["improvement_vs_baseline"] = {
        "overall_score_pct": round(metrics["overall_score_pct"] - BASELINE["overall_score_pct"], 2),
        "financial_routing_accuracy_pct": round(
            metrics["financial_routing_accuracy_pct"] - BASELINE["financial_routing_accuracy_pct"], 2
        ),
        "financial_engine_utilization_pct": round(
            metrics["financial_engine_utilization_pct"] - BASELINE["financial_engine_utilization_pct"], 2
        ),
        "generic_retrieval_pollution_pct": round(
            metrics["generic_retrieval_pollution_pct"] - BASELINE["generic_retrieval_pollution_pct"], 2
        ),
    }
    return metrics


def _release_decision(metrics: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    criteria = {
        "overall_score_pct >= 95": metrics["overall_score_pct"] >= 95.0,
        "financial_routing_accuracy_pct == 100": metrics["financial_routing_accuracy_pct"] == 100.0,
        "financial_engine_utilization_pct >= 95": metrics["financial_engine_utilization_pct"] >= 95.0,
        "generic_retrieval_pollution_pct <= 5 (target 0)": metrics["generic_retrieval_pollution_pct"] <= 5.0,
        "entity_misfire_count == 0": metrics["entity_misfire_count"] == 0,
        "recommendation_policy_accuracy_pct == 100": metrics["recommendation_policy_accuracy_pct"] == 100.0,
        "unknown_entity_accuracy_pct == 100": metrics["unknown_entity_accuracy_pct"] == 100.0,
        "hallucination_count == 0": metrics["hallucination_count"] == 0,
        "executive_answers_first_pct == 100": metrics["executive_answers_first_pct"] == 100.0,
    }
    passed = all(criteria.values())
    return {"pass": passed, "criteria": criteria}


_CATEGORY_TAXONOMY = (
    "routing", "financial_router", "financial_foundations", "financial_statement_intelligence",
    "retrieval", "entity_resolution", "executive_composer", "recommendation_policy",
    "unknown_entity_policy", "latency",
)


def _categorize_failure(row: Dict[str, Any]) -> str:
    """One category from _CATEGORY_TAXONOMY, derived only from observed
    orchestration/trace fields — never a guess."""
    flags = row.get("auto_fail_flags") or {}
    if row.get("http_status") not in (200,) and row.get("http_status") is not None:
        return "latency"
    if flags.get("recommendation_policy_regression"):
        return "recommendation_policy"
    if row.get("id") == "E39" or flags.get("hallucinated_entity"):
        return "unknown_entity_policy"
    if row.get("entity_misfire") or flags.get("wrong_company_injected"):
        return "entity_resolution"
    if flags.get("generic_retrieval_used"):
        engine = row.get("requires_engine")
        if row.get("financial_router_triggered") is False and engine:
            return "financial_router"
        return engine or "retrieval"
    if flags.get("framework_meta_leak") or flags.get("executive_did_not_answer_first"):
        return "executive_composer"
    if row.get("evidence_count", 0) == 0 and not row.get("retrieval_used"):
        return "retrieval"
    if (row.get("latency_ms") or 0) >= 100_000:
        return "latency"
    return "executive_composer"


def _expected_actual(row: Dict[str, Any]) -> tuple[str, str]:
    section = row.get("section")
    engine = row.get("requires_engine")
    if engine:
        expected = f"Answer sourced from {engine} (financial_router_triggered=True), no entity resolution required."
    elif row.get("id") in ("E37", "E38"):
        expected = "Refuses buy/sell/target-price with a monitoring-framed answer; no transactional advice."
    elif row.get("id") == "E39":
        expected = "Immediate 'I couldn't identify a verified company' refusal — no substitution, no fabricated narrative."
    else:
        expected = "Direct, evidence-grounded answer that addresses the question first."
    actual_bits = []
    if row.get("financial_router_triggered"):
        actual_bits.append(f"financial_router_triggered=True (engine={row.get('financial_engine')})")
    else:
        actual_bits.append("financial_router_triggered=False/absent")
    if row.get("auto_fail_flags"):
        actual_bits.append("auto_fail=" + ",".join(row["auto_fail_flags"]))
    actual_bits.append(f"score={row.get('final_score')}/30")
    return expected, "; ".join(actual_bits)


def _all_failures(rows: List[Dict[str, Any]], score_threshold: int = 25) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        if r["final_score"] >= score_threshold and not r["auto_fail_flags"]:
            continue
        expected, actual = _expected_actual(r)
        out.append(
            {
                "id": r["id"],
                "section": r["section"],
                "prompt": r["question"],
                "answer": (r.get("answer") or "")[:500],
                "expected_behavior": expected,
                "actual_behavior": actual,
                "root_cause_category": _categorize_failure(r),
                "auto_fail_flags": list(r["auto_fail_flags"]),
                "final_score": r["final_score"],
            }
        )
    return sorted(out, key=lambda x: x["final_score"])


def _top_failures(rows: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    return _all_failures(rows, score_threshold=31)[:n]  # 31 -> always "worst n", regardless of pass bar


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000")
    cooldown = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "6") or "6")
    h = AskProductHarness(latency_budget_ms=latency)
    out_dir = _artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    deployment_info = _deployment_info(h.base_url) if h.mode == "live" else {"commit": None, "environment": h.mode}
    print(
        f"[afi_acceptance_v1] mode={h.mode} base={h.base_url} cases={len(AFI_ACCEPTANCE_40)} cooldown={cooldown}s "
        f"commit={deployment_info.get('commit')}",
        flush=True,
    )

    rows: List[Dict[str, Any]] = []
    for i, case in enumerate(AFI_ACCEPTANCE_40, 1):
        if i > 1 and cooldown > 0 and h.mode == "live":
            time.sleep(cooldown)
        print(f"\n[{i}/40] {case['id']} ({case['section']}) — {case['prompt'][:90]}", flush=True)
        transport = h.ask(case["prompt"])
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = _evaluate_one(
            case, payload, latency_ms=transport.get("latency_ms") or 0, http_status=transport.get("http_status") or 0
        )
        row["raw_payload_excerpt"] = {
            "ask_trace_id": (payload.get("ask_orchestration") or {}).get("ask_trace_id") if isinstance(payload, dict) else None,
            "intent": payload.get("intent") if isinstance(payload, dict) else None,
        }
        rows.append(row)
        print(
            f"  score={row['final_score']}/30 auto_fail={list(row['auto_fail_flags'])} "
            f"engine_hit={row['engine_signal_found']} ms={row.get('latency_ms')}",
            flush=True,
        )
        print(f"  answer: {(row.get('answer') or '')[:220]}", flush=True)

        # Partial write after every case.
        partial = {
            "suite": "AGI Financial Intelligence Acceptance Test v1.0",
            "timestamp": _ts(),
            "mode": h.mode,
            "base_url": h.base_url,
            "partial": True,
            "completed_so_far": len(rows),
            "planned_total": len(AFI_ACCEPTANCE_40),
            "questions": rows,
        }
        _write_json(out_dir / "afi_acceptance_v1.json", partial)
        write_artifact("afi_acceptance_v1.json", partial)

    metrics = _compute_metrics(rows)
    decision = _release_decision(metrics, rows)
    top_failures = _top_failures(rows, 5)
    all_failures = _all_failures(rows)
    deployment = deployment_info

    report = {
        "suite": "AGI Financial Intelligence Acceptance Test v1.0",
        "timestamp": _ts(),
        "mode": h.mode,
        "base_url": h.base_url,
        "deployment": deployment,
        "total_questions": len(rows),
        "pass_mark_pct": 95,
        "metrics": metrics,
        "release_gate": decision,
        "top_5_failures": top_failures,
        "all_failures": all_failures,
        "questions": rows,
    }
    write_artifact("afi_acceptance_v1.json", report)
    write_artifact("afi_acceptance_report_live.json", report)
    summary_md = _render_summary_markdown(report)
    (out_dir / "afi_acceptance_summary.md").write_text(summary_md, encoding="utf-8")
    for mirror in mirror_artifact_dirs()[1:]:
        try:
            (mirror / "afi_acceptance_summary.md").write_text(summary_md, encoding="utf-8")
        except OSError:
            pass

    print(
        f"\n[afi_acceptance_v1] overall={metrics['overall_score_pct']}% "
        f"routing={metrics['financial_routing_accuracy_pct']}% "
        f"engine_util={metrics['financial_engine_utilization_pct']}% "
        f"pollution={metrics['generic_retrieval_pollution_pct']}% "
        f"decision={'PASS' if decision['pass'] else 'FAIL'}",
        flush=True,
    )
    print("\n" + _release_summary_text(report), flush=True)
    return 0 if decision["pass"] else 1


def _render_summary_markdown(report: Dict[str, Any]) -> str:
    m = report["metrics"]
    d = report["release_gate"]
    dep = report.get("deployment") or {}
    lines = [
        "# AGI Financial Intelligence Acceptance Test v1.0 — Live Release Gate",
        "",
        f"- Timestamp: {report['timestamp']}",
        f"- Mode: {report['mode']}",
        f"- Base URL: {report['base_url']}",
        f"- Commit: {dep.get('commit')}",
        f"- Total questions: {report['total_questions']}",
        "",
        "## Overall metrics",
        "",
        "| Metric | Value | Baseline | Δ |",
        "|---|---|---|---|",
        f"| Overall Score | {m['overall_score_pct']}% | {m['baseline']['overall_score_pct']}% | {m['improvement_vs_baseline']['overall_score_pct']:+.2f} |",
        f"| Financial Routing Accuracy | {m['financial_routing_accuracy_pct']}% | {m['baseline']['financial_routing_accuracy_pct']}% | {m['improvement_vs_baseline']['financial_routing_accuracy_pct']:+.2f} |",
        f"| Financial Engine Utilization | {m['financial_engine_utilization_pct']}% | {m['baseline']['financial_engine_utilization_pct']}% | {m['improvement_vs_baseline']['financial_engine_utilization_pct']:+.2f} |",
        f"| Generic Retrieval Pollution | {m['generic_retrieval_pollution_pct']}% | {m['baseline']['generic_retrieval_pollution_pct']}% | {m['improvement_vs_baseline']['generic_retrieval_pollution_pct']:+.2f} |",
        f"| Entity Misfires | {m['entity_misfire_count']} | — | — |",
        f"| Recommendation Policy Accuracy | {m['recommendation_policy_accuracy_pct']}% | — | — |",
        f"| Unknown Entity Accuracy | {m['unknown_entity_accuracy_pct']}% | — | — |",
        f"| Executive Composer Success | {m['executive_composer_success_pct']}% | — | — |",
        f"| Hallucination Count | {m['hallucination_count']} | — | — |",
        f"| P50 Latency (ms) | {m['latency_ms_p50']} | — | — |",
        f"| P95 Latency (ms) | {m['latency_ms_p95']} | — | — |",
        f"| Average Latency (ms) | {m['average_latency_ms']} | — | — |",
        "",
        "## By section",
        "",
        "| Section | Count | Avg Score | Avg % |",
        "|---|---|---|---|",
    ]
    for section, s in m["by_section"].items():
        lines.append(f"| {section} | {s['count']} | {s['avg_score']} | {s['avg_pct']}% |")

    lines += ["", "## Release gate", "", f"**Decision: {'PASS' if d['pass'] else 'FAIL'}**", "", "| Criterion | Met |", "|---|---|"]
    for k, v in d["criteria"].items():
        lines.append(f"| {k} | {'✅' if v else '❌'} |")

    if report["all_failures"]:
        lines += ["", "## Failing questions", ""]
        for f in report["all_failures"]:
            lines += [
                f"### {f['id']} ({f['section']}) — score {f['final_score']}/30",
                "",
                f"- Prompt: {f['prompt']}",
                f"- Answer: {f['answer']}",
                f"- Expected behavior: {f['expected_behavior']}",
                f"- Actual behavior: {f['actual_behavior']}",
                f"- Root cause category: `{f['root_cause_category']}`",
                f"- Auto-fail flags: {f['auto_fail_flags'] or 'none'}",
                "",
            ]
    else:
        lines += ["", "## Failing questions", "", "None — every question met the per-question passing bar."]

    return "\n".join(lines) + "\n"


def _release_summary_text(report: Dict[str, Any]) -> str:
    m = report["metrics"]
    d = report["release_gate"]
    dep = report.get("deployment") or {}
    passed = d["pass"]
    lines = [
        "Phase 2.5 Financial Intelligence Integration",
        "",
        f"Deployment: {report['base_url']}",
        f"Commit: {dep.get('commit') or 'unknown'}",
        f"Environment: {report['mode']}",
        "",
        f"Overall Score: {m['overall_score_pct']}%",
        f"Routing Accuracy: {m['financial_routing_accuracy_pct']}%",
        f"Financial Engine Utilization: {m['financial_engine_utilization_pct']}%",
        f"Generic Retrieval Pollution: {m['generic_retrieval_pollution_pct']}%",
        f"Recommendation Policy: {m['recommendation_policy_accuracy_pct']}%",
        f"Unknown Entity Policy: {m['unknown_entity_accuracy_pct']}%",
        f"Hallucinations: {m['hallucination_count']}",
        f"Average Latency: {m['average_latency_ms']} ms",
        "",
        f"Release Decision: {'PASS' if passed else 'FAIL'}",
    ]
    if not passed:
        lines += ["", "Blocking issues:"]
        for k, v in d["criteria"].items():
            if not v:
                lines.append(f"  - {k}")
    else:
        lines += [
            "",
            "Financial Foundations and Financial Statement Intelligence are now fully "
            "integrated into the live Ask production pipeline. Phase 2.5 can be frozen as v1.0.",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
