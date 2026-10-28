"""Aggregate judge dimensions into per-question and suite scores."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS


def score_question(
    question: dict[str, Any],
    judgments: list[dict[str, Any]],
) -> dict[str, Any]:
    by_dim = {j["dimension"]: j for j in judgments}
    weighted = 0.0
    weight_sum = 0.0
    failures: list[str] = []
    for dim, w in DIMENSION_WEIGHTS.items():
        j = by_dim.get(dim) or {}
        s = float(j.get("score") or 0.0)
        weighted += w * s
        weight_sum += w
        if j.get("passed") is False and j.get("root_cause"):
            failures.append(str(j["root_cause"]))
    overall = round(weighted / weight_sum if weight_sum else 0.0, 2)
    passed = overall >= 70.0 and not any(
        f in failures for f in ("fabricated_or_invented", "future_leakage", "quality_gate_fail")
    )
    dimensions = {d: by_dim.get(d, {}) for d in DIMENSION_WEIGHTS}
    # Independent Phase 4 metrics — never weighted into overall / CIO
    if "hypothesis_quality" in by_dim:
        dimensions["hypothesis_quality"] = by_dim["hypothesis_quality"]
    if "committee_quality" in by_dim:
        dimensions["committee_quality"] = by_dim["committee_quality"]
    if "confidence_quality" in by_dim:
        dimensions["confidence_quality"] = by_dim["confidence_quality"]
    if "thesis_quality" in by_dim:
        dimensions["thesis_quality"] = by_dim["thesis_quality"]
    if "decision_quality" in by_dim:
        dimensions["decision_quality"] = by_dim["decision_quality"]
    if "portfolio_quality" in by_dim:
        dimensions["portfolio_quality"] = by_dim["portfolio_quality"]
    if "monitoring_quality" in by_dim:
        dimensions["monitoring_quality"] = by_dim["monitoring_quality"]
    if "learning_quality" in by_dim:
        dimensions["learning_quality"] = by_dim["learning_quality"]
    hqs_val = None
    hq = dimensions.get("hypothesis_quality") or {}
    if hq and not hq.get("n_a"):
        hqs_val = hq.get("hqs") if hq.get("hqs") is not None else hq.get("score")
    cqs_val = None
    cq = dimensions.get("committee_quality") or {}
    if cq and not cq.get("n_a"):
        cqs_val = cq.get("cqs") if cq.get("cqs") is not None else cq.get("score")
    cfqs_val = None
    cfq = dimensions.get("confidence_quality") or {}
    if cfq and not cfq.get("n_a"):
        cfqs_val = cfq.get("cfqs") if cfq.get("cfqs") is not None else cfq.get("score")
    itqs_val = None
    tq = dimensions.get("thesis_quality") or {}
    if tq and not tq.get("n_a"):
        itqs_val = tq.get("itqs") if tq.get("itqs") is not None else tq.get("score")
    dqs_val = None
    dq = dimensions.get("decision_quality") or {}
    if dq and not dq.get("n_a"):
        dqs_val = dq.get("dqs") if dq.get("dqs") is not None else dq.get("score")
    pqs_val = None
    pq = dimensions.get("portfolio_quality") or {}
    if pq and not pq.get("n_a"):
        pqs_val = pq.get("pqs") if pq.get("pqs") is not None else pq.get("score")
    mqs_val = None
    mq = dimensions.get("monitoring_quality") or {}
    if mq and not mq.get("n_a"):
        mqs_val = mq.get("mqs") if mq.get("mqs") is not None else mq.get("score")
    lqs_val = None
    lq = dimensions.get("learning_quality") or {}
    if lq and not lq.get("n_a"):
        lqs_val = lq.get("lqs") if lq.get("lqs") is not None else lq.get("score")
    return {
        "question_id": question.get("question_id"),
        "question": question.get("question"),
        "category": question.get("category"),
        "difficulty": question.get("difficulty"),
        "sector": question.get("sector"),
        "suite": question.get("suite"),
        "ticker_hint": question.get("ticker_hint"),
        "overall": overall,
        "passed": passed,
        "dimensions": dimensions,
        "hqs": hqs_val,
        "cqs": cqs_val,
        "cfqs": cfqs_val,
        "itqs": itqs_val,
        "dqs": dqs_val,
        "pqs": pqs_val,
        "mqs": mqs_val,
        "lqs": lqs_val,
        "root_causes": failures,
        "verdict": "PASS" if passed else ("PARTIAL" if overall >= 55 else "FAIL"),
        # Expected labels for Root Cause Intelligence (Sprint 3.2)
        "expected_intent": list(question.get("intent") or []),
        "expected_framework": list(question.get("framework") or []),
        "expected_playbook": list(question.get("expected_playbook") or []),
        "expected_evidence": list(question.get("expected_evidence") or []),
        "expected_reasoning": list(question.get("expected_reasoning") or []),
        "tags": list(question.get("tags") or []),
    }


def aggregate_suite(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "pass_pct": 0.0,
            "mean_score": 0.0,
            "by_category": {},
            "by_verdict": {},
            "top_root_causes": [],
        }
    n = len(rows)
    passes = sum(1 for r in rows if r.get("passed"))
    mean_score = round(sum(float(r.get("overall") or 0) for r in rows) / n, 2)
    by_cat: dict[str, list[float]] = {}
    by_verdict: dict[str, int] = {}
    causes: dict[str, int] = {}
    for r in rows:
        cat = str(r.get("category") or "unknown")
        by_cat.setdefault(cat, []).append(float(r.get("overall") or 0))
        v = str(r.get("verdict") or "?")
        by_verdict[v] = by_verdict.get(v, 0) + 1
        for c in r.get("root_causes") or []:
            causes[str(c)] = causes.get(str(c), 0) + 1
    top_causes = sorted(causes.items(), key=lambda x: (-x[1], x[0]))[:20]
    return {
        "n": n,
        "pass_pct": round(100.0 * passes / n, 2),
        "mean_score": mean_score,
        "by_category": {
            k: {"n": len(v), "mean_score": round(sum(v) / len(v), 2)} for k, v in sorted(by_cat.items())
        },
        "by_verdict": by_verdict,
        "top_root_causes": [{"cause": c, "count": n_} for c, n_ in top_causes],
        "passed": passes,
        "failed": n - passes,
    }
