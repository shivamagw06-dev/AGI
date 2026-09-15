"""Learning Quality Score (LQS) — independent IEL metric for AGI v4.0 Sprint 5.5.

Does NOT change CIO / HQS / CQS / CFQS / ITQS / DQS / PQS / MQS weights.

Components:
  Learning usefulness · Root-cause quality · Lesson quality · Repeatability ·
  Actionability · Traceability · Replay consistency · Explainability

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

LQS_VERSION = "lqs-v1.0.0"

LQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "learning_usefulness": 0.14,
    "root_cause_quality": 0.14,
    "lesson_quality": 0.14,
    "repeatability": 0.10,
    "actionability": 0.14,
    "traceability": 0.12,
    "replay_consistency": 0.10,
    "explainability": 0.12,
}

_CATEGORIES = {
    "Evidence",
    "Framework",
    "Hypothesis",
    "Committee",
    "Monitoring",
    "Decision",
    "Portfolio",
    "Timing",
    "Macro",
    "Risk",
}

_ROOTS = {
    "Evidence",
    "Timing",
    "Macro",
    "Management",
    "Valuation",
    "Catalyst",
    "Execution",
    "Hypothesis",
    "Decision Process",
    "Unknown",
}


def _pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("learning_office") or {})


def _learning(pack: dict[str, Any]) -> dict[str, Any]:
    return dict(pack.get("learning") or {})


def _score_usefulness(learning: dict[str, Any]) -> tuple[float, str]:
    if not learning:
        return 20.0, "missing"
    score = 40.0
    if learning.get("lesson"):
        score += 30.0
    if learning.get("future_guidance"):
        score += 30.0
    return min(100.0, score), "present"


def _score_root_cause(learning: dict[str, Any]) -> tuple[float, str]:
    rc = str(learning.get("root_cause") or "")
    if rc in _ROOTS and rc != "Unknown":
        return 100.0, rc
    if rc == "Unknown":
        return 55.0, "unknown"
    if rc:
        return 40.0, f"other:{rc}"
    return 0.0, "missing"


def _score_lesson(learning: dict[str, Any]) -> tuple[float, str]:
    lesson = str(learning.get("lesson") or "").strip()
    if len(lesson) >= 40:
        return 100.0, "substantive"
    if len(lesson) >= 15:
        return 70.0, "short"
    if lesson:
        return 40.0, "thin"
    return 0.0, "missing"


def _score_repeatability(pack: dict[str, Any], learning: dict[str, Any]) -> tuple[float, str]:
    if pack.get("deterministic") is False or learning.get("llm_used"):
        return 20.0, "non_deterministic"
    if pack.get("deterministic") or learning.get("learning_id"):
        return 95.0, "deterministic"
    return 60.0, "partial"


def _score_actionability(learning: dict[str, Any]) -> tuple[float, str]:
    guidance = str(learning.get("future_guidance") or "").strip()
    if not guidance:
        return 20.0, "missing_guidance"
    actionable_markers = ("should", "require", "increase", "prefer", "tie", "stress-test", "future")
    hits = sum(1 for m in actionable_markers if m in guidance.lower())
    return min(100.0, 50.0 + 12.0 * hits), f"markers={hits}"


def _score_traceability(learning: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    notes = []
    for key, pts in (
        ("thesis_id", 25),
        ("decision_id", 20),
        ("portfolio_id", 20),
        ("linked_monitoring_events", 20),
        ("linked_evidence", 15),
    ):
        val = learning.get(key)
        if val not in (None, "", [], {}):
            score += pts
            notes.append(key)
    return min(100.0, score), ",".join(notes) or "none"


def _score_replay(pack: dict[str, Any], learning: dict[str, Any]) -> tuple[float, str]:
    if pack.get("knowledge_factory_updated"):
        return 0.0, "kf_updated"
    if learning.get("mutates_thesis") or pack.get("mutates_thesis"):
        return 0.0, "mutates_thesis"
    if pack.get("process_memory") is False:
        return 40.0, "not_process_memory"
    return 100.0, "process_memory_intact"


def _score_explainability(learning: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    for key, pts in (
        ("expected", 15),
        ("actual", 15),
        ("difference", 15),
        ("outcome", 15),
        ("category", 15),
        ("explanation", 15),
        ("questions_answered", 10),
    ):
        if learning.get(key) not in (None, "", {}):
            score += pts
    cat = str(learning.get("category") or "")
    if cat in _CATEGORIES:
        score = min(100.0, score + 5.0)
    return min(100.0, score), cat or "none"


def judge_learning_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    _ = question
    pack = _pack(probe)
    if not pack:
        return {
            "dimension": "learning_quality",
            "score": None,
            "lqs": None,
            "passed": True,
            "n_a": True,
            "lqs_version": LQS_VERSION,
            "independent_of_cio": True,
            "independent_of_mqs": True,
            "root_cause": None,
            "components": {},
            "note": "No learning_office pack on probe",
        }

    learning = _learning(pack)
    scorers = {
        "learning_usefulness": lambda: _score_usefulness(learning),
        "root_cause_quality": lambda: _score_root_cause(learning),
        "lesson_quality": lambda: _score_lesson(learning),
        "repeatability": lambda: _score_repeatability(pack, learning),
        "actionability": lambda: _score_actionability(learning),
        "traceability": lambda: _score_traceability(learning),
        "replay_consistency": lambda: _score_replay(pack, learning),
        "explainability": lambda: _score_explainability(learning),
    }
    components: dict[str, dict[str, Any]] = {}
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": LQS_COMPONENT_WEIGHTS[name]}

    lqs = 0.0
    for name, w in LQS_COMPONENT_WEIGHTS.items():
        lqs += w * float(components[name]["score"])
    lqs = round(lqs, 2)
    passed = lqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None if passed else f"lqs_weak_{worst[0]}"

    return {
        "dimension": "learning_quality",
        "score": lqs,
        "lqs": lqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(LQS_COMPONENT_WEIGHTS),
        "components": components,
        "learning_id": learning.get("learning_id"),
        "outcome": learning.get("outcome"),
        "category": learning.get("category"),
        "knowledge_factory_updated": False,
        "lqs_version": LQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "independent_of_cfqs": True,
        "independent_of_itqs": True,
        "independent_of_dqs": True,
        "independent_of_pqs": True,
        "independent_of_mqs": True,
        "root_cause": root,
    }


def aggregate_lqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in LQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("learning_quality")) or r.get("learning_quality") or {}
        if j.get("n_a") or (j.get("lqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("lqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in LQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    return {
        "lqs_version": LQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_lqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "note": "LQS does not affect IEL overall / CIO / prior Phase 4–5 metric weights",
    }
