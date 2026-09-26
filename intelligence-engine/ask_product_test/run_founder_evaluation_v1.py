#!/usr/bin/env python3
"""AGI Founder Evaluation v1.0 — production release gate.

Runs the full 20-question founder evaluation against LIVE Ask (or inprocess),
judging only the user-visible answer. Writes:

  artifacts/founder_evaluation_v1.json
  artifacts/founder_failure_report.json   (only if any question scores < 20)

Release PASS requires: average >= 25/30, no hard-fail flags, no fallback,
no HTML/502.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ask_product_test.founder_evaluation_v1 import FOUNDER_EVAL_20, evaluate_payload
from ask_product_test.harness import AskProductHarness, _artifacts_dir


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _classify_failure(row: Dict[str, Any]) -> Dict[str, Any]:
    """Root-cause classification for founder_failure_report.json."""
    flags = row.get("hard_fail_flags") or {}
    dims = row.get("dimension_scores") or {}
    executive_composer_issue = bool(
        flags.get("framework_scaffold_leak")
        or flags.get("unknown_entity_hallucinated")
        or flags.get("unknown_entity_substituted_company")
        or flags.get("comparison_omits_entity")
        or flags.get("recommendation_policy_regression")
    )
    retrieval_issue = row.get("retrieved", 0) == 0 and not executive_composer_issue
    entity_issue = (
        not row.get("entity")
        and row.get("section") not in {"Unknown Entity", "Institutional Knowledge", "Macro"}
        and not executive_composer_issue
    )
    ikl_issue = row.get("section") == "Historical" and dims.get("reasoning", 0) <= 2
    recommendation_policy_issue = row.get("section") == "Recommendation Policy" and bool(
        flags.get("recommendation_policy_regression")
    )

    expected = {
        "Company Intelligence": "Direct business-model explanation with segments/drivers/risks.",
        "Earnings Intelligence": "Direct management-commentary summary on the requested topic.",
        "Institutional Knowledge": "Concept-level teaching answer (no company substitution needed).",
        "Macro": "Cross-sector or macro reasoning grounded in evidence.",
        "Historical": "Point-in-time answer that respects the as_of date (no look-ahead).",
        "Unknown Entity": "Immediate 'I couldn't identify...' refusal — no retrieval, no substitution.",
        "Recommendation Policy": "No BUY/SELL or price target — monitoring framework only.",
        "Deep Research": "Comparative/synthesized institutional reasoning across ≥2 sources or entities.",
    }.get(row.get("section"), "Direct, evidence-grounded answer to the question asked.")

    suggested_fix = []
    if flags.get("framework_scaffold_leak"):
        suggested_fix.append("Executive Composer scaffold ban regressed or missed a new leak pattern.")
    if flags.get("unknown_entity_hallucinated") or flags.get("unknown_entity_substituted_company"):
        suggested_fix.append("Unknown-entity hard stop not applied before this path.")
    if flags.get("comparison_omits_entity"):
        suggested_fix.append("Comparison ≥2-entity gate not enforced for this phrasing.")
    if flags.get("recommendation_policy_regression"):
        suggested_fix.append("Recommendation-bait detector missed this phrasing — extend pattern list.")
    if retrieval_issue:
        suggested_fix.append("No evidence retrieved — check source availability for this topic/entity.")
    if entity_issue:
        suggested_fix.append("Entity resolution did not bind a company for a company-shaped question.")
    if ikl_issue:
        suggested_fix.append("Historical/point-in-time reasoning (IKL) did not respect as_of constraint.")
    if not suggested_fix:
        suggested_fix.append("Improve topical coverage / evidence depth for this question type.")

    return {
        "question": row.get("question"),
        "section": row.get("section"),
        "expected_behavior": expected,
        "actual_behavior": (row.get("answer") or "")[:400],
        "root_cause": {
            "executive_composer_issue": executive_composer_issue,
            "retrieval_issue": retrieval_issue,
            "entity_issue": entity_issue,
            "ikl_issue": ikl_issue,
            "recommendation_policy_issue": recommendation_policy_issue,
        },
        "hard_fail_flags": list(flags),
        "final_score": row.get("final_score"),
        "suggested_fix": " ".join(suggested_fix),
    }


def main() -> int:
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000")
    cooldown = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "12") or "12")
    h = AskProductHarness(latency_budget_ms=latency)
    out_dir = _artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    ws = Path("/workspace/artifacts")
    ws.mkdir(parents=True, exist_ok=True)

    print(
        f"[founder_eval_v1] mode={h.mode} base={h.base_url} cases={len(FOUNDER_EVAL_20)} "
        f"cooldown={cooldown}s",
        flush=True,
    )

    results: List[Dict[str, Any]] = []
    for i, case in enumerate(FOUNDER_EVAL_20, 1):
        if i > 1 and cooldown > 0 and h.mode == "live":
            time.sleep(cooldown)
        print(f"\n[{i}/20] {case['id']} ({case['section']}) — {case['prompt'][:90]}", flush=True)
        transport = h.ask(case["prompt"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = evaluate_payload(
            case,
            payload if isinstance(payload, dict) else {},
            latency_ms=transport.get("latency_ms"),
            http_status=transport.get("http_status"),
            raw_html=bool(transport.get("raw_is_html")),
        )
        results.append(row)
        print(
            f"  score={row['final_score']}/30 hard_fail={list(row['hard_fail_flags'])} "
            f"ms={row.get('latency_ms')}",
            flush=True,
        )
        print(f"  answer: {(row.get('answer') or '')[:220]}", flush=True)
        # Write partial after every case so a hang doesn't lose progress.
        _write_partial(ws, out_dir, results, mode=h.mode, base_url=h.base_url, partial=True)

    avg_score = round(sum(r["final_score"] for r in results) / max(1, len(results)), 2)
    hard_fail_union: Dict[str, bool] = {}
    for r in results:
        for k in r.get("hard_fail_flags") or {}:
            hard_fail_union[k] = True
    fallback_any = any(r.get("hard_fail_flags", {}).get("fallback_response") for r in results)
    html_any = any(r.get("hard_fail_flags", {}).get("html_or_non_200_response") for r in results)

    release_pass = (
        avg_score >= 25
        and not hard_fail_union
        and not fallback_any
        and not html_any
    )

    report = {
        "suite": "AGI Founder Evaluation v1.0 (Production Release Gate)",
        "timestamp": _ts(),
        "mode": h.mode,
        "base_url": h.base_url,
        "total_questions": len(results),
        "average_score": avg_score,
        "max_score": 30,
        "hard_fail_flags": hard_fail_union,
        "fallback_responses": fallback_any,
        "html_or_502": html_any,
        "release_criteria": {
            "average_score_min": 25,
            "no_hard_fail_flags": True,
            "no_framework_leakage": True,
            "no_hallucinated_entities": True,
            "no_recommendation_regression": True,
            "no_comparison_failures": True,
            "no_fallback_responses": True,
            "no_html_502": True,
        },
        "release_decision": "PASS" if release_pass else "FAIL",
        "questions": results,
    }
    _write_final(ws, out_dir, report)

    failures = [r for r in results if r["final_score"] < 20]
    if failures:
        failure_report = {
            "suite": "AGI Founder Evaluation v1.0 — Failure Report",
            "timestamp": _ts(),
            "count": len(failures),
            "threshold": 20,
            "failures": [_classify_failure(r) for r in failures],
        }
        _write_json(ws / "founder_failure_report.json", failure_report)
        _write_json(out_dir / "founder_failure_report.json", failure_report)
        print(f"\n[founder_eval_v1] wrote failure report ({len(failures)} case(s) < 20/30)", flush=True)

    print(
        f"\n[founder_eval_v1] avg_score={avg_score}/30 decision={report['release_decision']} "
        f"hard_fail_flags={list(hard_fail_union)}",
        flush=True,
    )
    return 0 if release_pass else 1


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _write_partial(
    ws: Path, out_dir: Path, results: List[Dict[str, Any]], *, mode: str, base_url: str, partial: bool
) -> None:
    avg = round(sum(r["final_score"] for r in results) / max(1, len(results)), 2) if results else 0.0
    partial_report = {
        "suite": "AGI Founder Evaluation v1.0 (Production Release Gate)",
        "timestamp": _ts(),
        "mode": mode,
        "base_url": base_url,
        "partial": partial,
        "completed_so_far": len(results),
        "planned_total": len(FOUNDER_EVAL_20),
        "average_score_so_far": avg,
        "questions": results,
    }
    _write_json(ws / "founder_evaluation_v1.json", partial_report)
    _write_json(out_dir / "founder_evaluation_v1.json", partial_report)


def _write_final(ws: Path, out_dir: Path, report: Dict[str, Any]) -> None:
    _write_json(ws / "founder_evaluation_v1.json", report)
    _write_json(out_dir / "founder_evaluation_v1.json", report)


if __name__ == "__main__":
    raise SystemExit(main())
