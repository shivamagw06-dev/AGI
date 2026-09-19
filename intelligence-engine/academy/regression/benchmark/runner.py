"""Run frozen golden benchmark for a release."""

from __future__ import annotations

from typing import Any

from academy.regression.analyst_drift.detector import detect_drift
from academy.regression.analyst_drift.detector import summarize as summarize_drift
from academy.regression.benchmark.responder import respond
from academy.regression.evaluation.scorer import score_response
from academy.regression.golden_answers.loader import load_answers
from academy.regression.golden_questions.loader import load_questions
from academy.regression.golden_set.v1.companies import universe_counts
from academy.regression.hallucination.audit import audit_text
from academy.regression.hallucination.audit import summarize as summarize_hallucinations
from academy.regression.schema import GOLDEN_SET_VERSION, IRS_VERSION


def run_benchmark(*, golden_version: str = GOLDEN_SET_VERSION) -> dict[str, Any]:
    questions = load_questions(golden_version)
    answers = load_answers(golden_version)

    per_question: list[dict[str, Any]] = []
    all_hall = []
    all_drift = []
    domain_scores: dict[str, list[float]] = {}
    analyst_scores: dict[str, list[float]] = {}
    calibration: list[dict[str, Any]] = []

    for q in questions:
        ref = answers[q.question_id]
        resp = respond(q)
        scored = score_response(q, ref, resp["answer"], resp.get("structure"))
        halls = audit_text(q.question_id, resp["answer"], structure=resp.get("structure"))
        drifts = detect_drift(q.analyst, q.question_id, resp["answer"])
        all_hall.extend(halls)
        all_drift.extend(drifts)

        conf = float(resp.get("confidence") or 0.7)
        evidence = float(scored["evidence_score"])
        # Confidence calibration: high conf needs high evidence
        if conf >= 0.8 and evidence < 60:
            cal_flag = "overconfidence"
        elif conf <= 0.6 and evidence >= 85:
            cal_flag = "underconfidence"
        else:
            cal_flag = "calibrated"
        calibration.append(
            {
                "question_id": q.question_id,
                "confidence": conf,
                "evidence_score": evidence,
                "flag": cal_flag,
            }
        )

        domain_scores.setdefault(q.domain, []).append(scored["overall"])
        analyst_scores.setdefault(q.analyst, []).append(scored["overall"])
        per_question.append(
            {
                **scored,
                "confidence": conf,
                "calibration": cal_flag,
                "answer_preview": (resp["answer"] or "")[:400],
                "hallucinations": len(halls),
                "drifts": len(drifts),
                "source": resp.get("source"),
            }
        )

    def avg(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    reasoning_rollup = {
        "business": avg(domain_scores.get("business", [])),
        "financial": avg(domain_scores.get("financial", [])),
        "valuation": avg(domain_scores.get("valuation", [])),
        "risk": avg(domain_scores.get("risk", [])),
        "macro": avg(domain_scores.get("macro", [])),
        "sector": avg(domain_scores.get("sector", [])),
        "management": avg(domain_scores.get("management", [])),
        "portfolio": avg(domain_scores.get("portfolio", [])),
        "committee": avg(analyst_scores.get("committee", [])),
        "cio": avg(analyst_scores.get("cio", [])),
        "research_writer": avg(analyst_scores.get("research_writer", [])),
    }
    # Soft fill committee/cio/IRW from related domains when no dedicated golden Qs
    if not reasoning_rollup["committee"]:
        reasoning_rollup["committee"] = round(
            (
                reasoning_rollup["business"]
                + reasoning_rollup["financial"]
                + reasoning_rollup["valuation"]
                + reasoning_rollup["risk"]
            )
            / 4,
            2,
        )
    if not reasoning_rollup["cio"]:
        reasoning_rollup["cio"] = round(
            (reasoning_rollup["committee"] + reasoning_rollup["portfolio"]) / 2
            if reasoning_rollup["portfolio"]
            else reasoning_rollup["committee"],
            2,
        )
    if not reasoning_rollup["research_writer"]:
        reasoning_rollup["research_writer"] = round(
            (reasoning_rollup["committee"] + reasoning_rollup["cio"]) / 2, 2
        )

    overall = avg([x["overall"] for x in per_question])
    hall_sum = summarize_hallucinations(all_hall)
    drift_sum = summarize_drift(all_drift)
    overconf = sum(1 for c in calibration if c["flag"] == "overconfidence")

    return {
        "irs_version": IRS_VERSION,
        "golden_set_version": golden_version,
        "immutable_golden_set": True,
        "universe": universe_counts(),
        "questions_run": len(per_question),
        "per_question": per_question,
        "reasoning_scores": reasoning_rollup,
        "analyst_scores": {k: avg(v) for k, v in analyst_scores.items()},
        "overall_institutional_iq": overall,
        "evidence_score_mean": avg([x["evidence_score"] for x in per_question]),
        "framework_score_mean": avg([x["framework_score"] for x in per_question]),
        "hallucinations": hall_sum,
        "analyst_drift": drift_sum,
        "confidence_calibration": {
            "items": calibration,
            "overconfidence": overconf,
            "underconfidence": sum(1 for c in calibration if c["flag"] == "underconfidence"),
            "calibrated": sum(1 for c in calibration if c["flag"] == "calibrated"),
        },
        "knowledge_retention": _retention(per_question),
        "case_transfer": _case_transfer(per_question),
    }


def _retention(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ret = [r for r in rows if "ret" in r["question_id"] or r.get("domain") == "financial"]
    # specifically gq_ret_roic
    hit = next((r for r in rows if r["question_id"] == "gq_ret_roic"), None)
    return {
        "roic_synthesis_retained": bool(hit and hit["overall"] >= 70),
        "score": hit["overall"] if hit else 0.0,
    }


def _case_transfer(rows: list[dict[str, Any]]) -> dict[str, Any]:
    xfers = [r for r in rows if r["question_id"].startswith("gq_xfer_")]
    return {
        "count": len(xfers),
        "mean_score": round(sum(r["overall"] for r in xfers) / max(1, len(xfers)), 2),
        "all_pass": all(r["overall"] >= 70 for r in xfers) if xfers else False,
    }
