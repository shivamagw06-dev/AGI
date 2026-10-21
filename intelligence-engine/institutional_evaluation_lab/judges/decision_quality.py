"""Decision Quality Score (DQS) — independent IEL metric for AGI v4.0 Sprint 5.2.

Does NOT change CIO / HQS / CQS / CFQS / ITQS weights.

Components:
  Decision consistency · Decision traceability · Decision explainability ·
  Trigger quality · Review quality · Lifecycle quality ·
  Separation of analysis and decision

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

DQS_VERSION = "dqs-v1.0.0"

DQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "decision_consistency": 0.16,
    "decision_traceability": 0.14,
    "decision_explainability": 0.16,
    "trigger_quality": 0.14,
    "review_quality": 0.12,
    "lifecycle_quality": 0.12,
    "analysis_decision_separation": 0.16,
}

_ALLOWED = {
    "Wait",
    "Monitor",
    "Increase Research",
    "Reject",
    "Escalate",
    "Approve",
    "Review After Earnings",
    "Review After Budget",
    "Review After Results",
}

_LIFECYCLE = {
    "Watch",
    "Research",
    "Committee Review",
    "Approved",
    "Monitoring",
    "Closed",
}


def _pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("decision_office") or {})


def _dec(pack: dict[str, Any]) -> dict[str, Any]:
    return dict(pack.get("decision") or {})


def _score_consistency(d: dict[str, Any]) -> tuple[float, str]:
    if not d:
        return 0.0, "no_decision"
    decision = str(d.get("decision") or "")
    if decision in {"BUY", "SELL", "Buy", "Sell"} or d.get("buy_sell") is not None:
        return 0.0, "buy_sell_emitted"
    if d.get("orders") is not None or d.get("execution") is True:
        return 0.0, "execution_present"
    if decision not in _ALLOWED:
        return 30.0, f"unknown_decision:{decision}"
    return 100.0, decision


def _score_traceability(d: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    notes = []
    if d.get("thesis_id"):
        score += 35
        notes.append("thesis")
    if d.get("dependencies"):
        score += 25
        notes.append("deps")
    if d.get("provenance"):
        score += 20
        notes.append("prov")
    if d.get("decision_id"):
        score += 20
        notes.append("id")
    return min(100.0, score), ",".join(notes) or "none"


def _score_explainability(d: dict[str, Any]) -> tuple[float, str]:
    reason = str(d.get("reason") or "")
    if not reason:
        return 0.0, "no_reason"
    score = 50.0
    if reason.lower().startswith("decision:"):
        score += 20
    if d.get("required_conditions"):
        score += 15
    if "not an order" in reason.lower() or "not imply action" in reason.lower() or "process" in reason.lower():
        score += 15
    return min(100.0, score), "ok"


def _score_trigger(d: dict[str, Any]) -> tuple[float, str]:
    trig = str(d.get("review_trigger") or "")
    if not trig:
        return 20.0, "missing_trigger"
    return 100.0, trig[:40]


def _score_review(d: dict[str, Any]) -> tuple[float, str]:
    if d.get("review_date") and d.get("review_trigger"):
        return 100.0, "date+trigger"
    if d.get("review_date") or d.get("review_trigger"):
        return 60.0, "partial"
    return 20.0, "missing"


def _score_lifecycle(d: dict[str, Any]) -> tuple[float, str]:
    status = str(d.get("status") or d.get("lifecycle") or "")
    if status in _LIFECYCLE:
        return 100.0, status
    if status:
        return 40.0, f"nonstandard:{status}"
    return 0.0, "missing"


def _score_separation(d: dict[str, Any], pack: dict[str, Any], probe: dict[str, Any]) -> tuple[float, str]:
    score = 100.0
    notes = []
    if d.get("analysis_decision_separated") is not True:
        score -= 30
        notes.append("flag_false")
    if pack.get("buy_sell_emitted") or pack.get("orders_emitted"):
        return 0.0, "orders_or_buysell"
    if d.get("judgment_stack_modified") or d.get("thesis_modified"):
        return 0.0, "mutated_upstream"
    # Thesis may be positive while decision is Wait — that is good separation
    thesis = ((probe.get("investment_thesis") or {}).get("thesis") or {})
    view = str(thesis.get("investment_view") or "").lower()
    decision = str(d.get("decision") or "")
    if decision == "Wait" and view and "insufficient" not in view:
        notes.append("positive_analysis_wait_ok")
    return max(0.0, score), ",".join(notes) or "separated"


def judge_decision_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    _ = question
    pack = _pack(probe)
    if not pack:
        return {
            "dimension": "decision_quality",
            "score": None,
            "dqs": None,
            "passed": True,
            "n_a": True,
            "dqs_version": DQS_VERSION,
            "independent_of_cio": True,
            "independent_of_itqs": True,
            "root_cause": None,
            "components": {},
            "note": "No decision_office pack on probe",
        }

    d = _dec(pack)
    scorers = {
        "decision_consistency": lambda: _score_consistency(d),
        "decision_traceability": lambda: _score_traceability(d),
        "decision_explainability": lambda: _score_explainability(d),
        "trigger_quality": lambda: _score_trigger(d),
        "review_quality": lambda: _score_review(d),
        "lifecycle_quality": lambda: _score_lifecycle(d),
        "analysis_decision_separation": lambda: _score_separation(d, pack, probe),
    }
    components: dict[str, dict[str, Any]] = {}
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": DQS_COMPONENT_WEIGHTS[name]}

    dqs = 0.0
    for name, w in DQS_COMPONENT_WEIGHTS.items():
        dqs += w * float(components[name]["score"])
    dqs = round(dqs, 2)
    passed = dqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None if passed else f"dqs_weak_{worst[0]}"

    return {
        "dimension": "decision_quality",
        "score": dqs,
        "dqs": dqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(DQS_COMPONENT_WEIGHTS),
        "components": components,
        "decision": d.get("decision"),
        "status": d.get("status"),
        "orders_emitted": False,
        "dqs_version": DQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "independent_of_cfqs": True,
        "independent_of_itqs": True,
        "root_cause": root,
    }


def aggregate_dqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in DQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("decision_quality")) or r.get("decision_quality") or {}
        if j.get("n_a") or (j.get("dqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("dqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in DQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    return {
        "dqs_version": DQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_dqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "note": "DQS does not affect IEL overall / CIO / HQS / CQS / CFQS / ITQS weights",
    }
