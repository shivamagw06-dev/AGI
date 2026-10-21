"""Investment Thesis Quality Score (ITQS) — independent IEL metric for AGI v4.0 Sprint 5.1.

Does NOT change CIO / HQS / CQS / CFQS weights.

Components:
  Completeness · Internal consistency · Evidence traceability · Thesis versioning ·
  Catalyst quality · Risk quality · Invalidation quality · Monitoring quality ·
  Update quality · Explainability

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

ITQS_VERSION = "itqs-v1.0.0"

ITQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "completeness": 0.14,
    "internal_consistency": 0.10,
    "evidence_traceability": 0.12,
    "thesis_versioning": 0.08,
    "catalyst_quality": 0.10,
    "risk_quality": 0.10,
    "invalidation_quality": 0.10,
    "monitoring_quality": 0.10,
    "update_quality": 0.06,
    "explainability": 0.10,
}

_REQUIRED = (
    "thesis_id",
    "company",
    "investment_view",
    "why_now",
    "what_market_missing",
    "decision_status",
    "lifecycle",
    "confidence",
    "confidence_reason",
    "version",
    "owner",
    "monitoring_checklist",
)


def _pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("investment_thesis") or {})


def _thesis(pack: dict[str, Any]) -> dict[str, Any]:
    return dict(pack.get("thesis") or {})


def _score_completeness(t: dict[str, Any]) -> tuple[float, str]:
    if not t:
        return 0.0, "no_thesis"
    filled = sum(1 for k in _REQUIRED if t.get(k) not in (None, "", []))
    # cases + evidence
    for k in ("bull_case", "base_case", "bear_case", "supporting_evidence", "catalysts", "risks", "invalidation"):
        if t.get(k):
            filled += 1
    total = len(_REQUIRED) + 7
    score = round(100.0 * filled / total, 1)
    return min(100.0, score), f"{filled}/{total}"


def _score_consistency(t: dict[str, Any]) -> tuple[float, str]:
    if not t:
        return 0.0, "no_thesis"
    score = 100.0
    notes = []
    if t.get("buy_sell") is not None:
        return 0.0, "buy_sell_present"
    if str(t.get("decision_status") or "") in {"BUY", "SELL", "Buy", "Sell"}:
        return 0.0, "forbidden_decision"
    if t.get("analysis_only") is False:
        score -= 20
        notes.append("analysis_only_false")
    if t.get("judgment_stack_modified") is True:
        return 0.0, "judgment_modified"
    # If confidence present, reason should mention it
    conf = t.get("confidence")
    reason = str(t.get("confidence_reason") or "")
    if conf is not None and reason and str(int(conf)) not in reason and "/100" not in reason:
        score -= 15
        notes.append("reason_mismatch")
    return max(0.0, score), ",".join(notes) or "ok"


def _score_evidence(t: dict[str, Any]) -> tuple[float, str]:
    sup = t.get("supporting_evidence") or []
    if not sup:
        return 30.0, "no_supporting"
    score = 70.0
    if t.get("counter_evidence") is not None:
        score += 15.0
    if t.get("citations") or any(isinstance(x, dict) and x.get("evidence_id") for x in sup):
        score += 15.0
    return min(100.0, score), f"n_support={len(sup)}"


def _score_versioning(t: dict[str, Any]) -> tuple[float, str]:
    ver = str(t.get("version") or "")
    if not ver:
        return 0.0, "missing_version"
    if "." not in ver:
        return 50.0, "unstructured_version"
    return 100.0, f"version={ver}"


def _score_list_field(t: dict[str, Any], key: str) -> tuple[float, str]:
    v = t.get(key) or []
    if not isinstance(v, list):
        return 20.0, "not_list"
    if len(v) == 0:
        # Allowed if committee had no cases for that dimension — soft credit if monitoring exists
        if key in {"catalysts", "risks", "invalidation"} and (t.get("monitoring_checklist") or []):
            return 55.0, "empty_but_monitoring"
        return 25.0, "empty"
    return min(100.0, 60.0 + 10.0 * min(4, len(v))), f"n={len(v)}"


def _score_monitoring(t: dict[str, Any]) -> tuple[float, str]:
    m = t.get("monitoring_checklist") or []
    if not m:
        return 0.0, "missing"
    score = min(100.0, 50.0 + 10.0 * min(5, len(m)))
    blob = " ".join(str(x) for x in m).lower()
    if "earnings" in blob:
        score = min(100.0, score + 10.0)
    return score, f"n={len(m)}"


def _score_update(t: dict[str, Any]) -> tuple[float, str]:
    if t.get("last_updated") and t.get("created_at"):
        return 100.0, "timestamps_present"
    if t.get("last_updated"):
        return 80.0, "last_updated_only"
    return 40.0, "missing_timestamps"


def _score_explainability(t: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    notes = []
    if t.get("investment_view"):
        score += 25
        notes.append("view")
    if t.get("why_now"):
        score += 15
        notes.append("why_now")
    if t.get("what_market_missing"):
        score += 15
        notes.append("missing")
    if t.get("confidence_reason"):
        score += 25
        notes.append("confidence_reason")
    if t.get("ten_questions"):
        score += 20
        notes.append("ten_q")
    return min(100.0, score), ",".join(notes) or "none"


def judge_thesis_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    _ = question
    pack = _pack(probe)
    if not pack:
        return {
            "dimension": "thesis_quality",
            "score": None,
            "itqs": None,
            "passed": True,
            "n_a": True,
            "itqs_version": ITQS_VERSION,
            "independent_of_cio": True,
            "independent_of_hqs": True,
            "independent_of_cqs": True,
            "independent_of_cfqs": True,
            "root_cause": None,
            "components": {},
            "note": "No investment_thesis pack on probe",
        }

    t = _thesis(pack)
    scorers = {
        "completeness": lambda: _score_completeness(t),
        "internal_consistency": lambda: _score_consistency(t),
        "evidence_traceability": lambda: _score_evidence(t),
        "thesis_versioning": lambda: _score_versioning(t),
        "catalyst_quality": lambda: _score_list_field(t, "catalysts"),
        "risk_quality": lambda: _score_list_field(t, "risks"),
        "invalidation_quality": lambda: _score_list_field(t, "invalidation"),
        "monitoring_quality": lambda: _score_monitoring(t),
        "update_quality": lambda: _score_update(t),
        "explainability": lambda: _score_explainability(t),
    }
    components: dict[str, dict[str, Any]] = {}
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": ITQS_COMPONENT_WEIGHTS[name]}

    itqs = 0.0
    for name, w in ITQS_COMPONENT_WEIGHTS.items():
        itqs += w * float(components[name]["score"])
    itqs = round(itqs, 2)
    passed = itqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None if passed else f"itqs_weak_{worst[0]}"

    return {
        "dimension": "thesis_quality",
        "score": itqs,
        "itqs": itqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(ITQS_COMPONENT_WEIGHTS),
        "components": components,
        "thesis_id": t.get("thesis_id"),
        "decision_status": t.get("decision_status"),
        "lifecycle": t.get("lifecycle"),
        "buy_sell_emitted": False,
        "itqs_version": ITQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "independent_of_cfqs": True,
        "root_cause": root,
    }


def aggregate_itqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in ITQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("thesis_quality")) or r.get("thesis_quality") or {}
        if j.get("n_a") or (j.get("itqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("itqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in ITQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    return {
        "itqs_version": ITQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_itqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "note": "ITQS does not affect IEL overall / CIO / HQS / CQS / CFQS weights",
    }
