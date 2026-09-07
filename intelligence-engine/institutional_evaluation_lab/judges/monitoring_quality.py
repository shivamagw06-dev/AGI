"""Monitoring Quality Score (MQS) — independent IEL metric for AGI v4.0 Sprint 5.4.

Does NOT change CIO / HQS / CQS / CFQS / ITQS / DQS / PQS weights.

Components:
  Trigger relevance · False-positive discipline · Event traceability ·
  Review recommendation quality · Latency proxy · Monitoring coverage ·
  Explainability

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

MQS_VERSION = "mqs-v1.0.0"

MQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "trigger_relevance": 0.16,
    "false_positive_discipline": 0.14,
    "event_traceability": 0.16,
    "review_recommendation_quality": 0.16,
    "latency": 0.10,
    "monitoring_coverage": 0.14,
    "explainability": 0.14,
}

_ACTIONS = {
    "Review",
    "Committee Review",
    "Escalate",
    "Refresh Thesis",
    "Monitor",
    "No Action",
}

_DOMAINS = {
    "Earnings",
    "Guidance",
    "Management Commentary",
    "Corporate Actions",
    "Regulatory",
    "Macro",
    "Sector",
    "Competitor",
    "Valuation",
    "Confidence",
}


def _pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("monitoring_office") or {})


def _events(pack: dict[str, Any]) -> list[dict[str, Any]]:
    rows = pack.get("events") or []
    return [e for e in rows if isinstance(e, dict)]


def _score_trigger_relevance(events: list[dict[str, Any]]) -> tuple[float, str]:
    if not events:
        return 30.0, "no_events"
    scored = 0.0
    n = 0
    for e in events:
        trig = e.get("trigger") if isinstance(e.get("trigger"), dict) else {}
        code = str(trig.get("code") or "")
        domain = str(trig.get("domain") or "")
        n += 1
        pts = 40.0
        if code:
            pts += 30.0
        if domain in _DOMAINS:
            pts += 30.0
        scored += min(100.0, pts)
    return round(scored / max(1, n), 2), f"n={n}"


def _score_false_positive(events: list[dict[str, Any]], pack: dict[str, Any]) -> tuple[float, str]:
    # Discipline: heartbeat alone is OK; critical actions must have review flag;
    # mutates_* must be false.
    if pack.get("mutates_thesis") or pack.get("mutates_decision") or pack.get("mutates_portfolio"):
        return 0.0, "mutates_objects"
    if not events:
        return 50.0, "empty"
    bad = 0
    for e in events:
        if e.get("mutates_thesis") or e.get("mutates_decision") or e.get("mutates_portfolio"):
            bad += 1
        action = str(e.get("recommended_action") or "")
        if action in {"Committee Review", "Escalate", "Refresh Thesis"} and not e.get("requires_review"):
            bad += 1
        if action not in _ACTIONS:
            bad += 1
    rate = bad / max(1, len(events))
    return round(max(0.0, 100.0 - 100.0 * rate), 2), f"bad={bad}"


def _score_traceability(events: list[dict[str, Any]], pack: dict[str, Any]) -> tuple[float, str]:
    if not events:
        return 20.0, "no_events"
    score = 50.0
    if pack.get("portfolio_idea") or all(e.get("portfolio_idea") for e in events):
        score += 20.0
    if any(e.get("affected_thesis") for e in events):
        score += 15.0
    if any(e.get("affected_decision") for e in events):
        score += 15.0
    return min(100.0, score), "linked"


def _score_review_recs(events: list[dict[str, Any]]) -> tuple[float, str]:
    if not events:
        return 30.0, "no_events"
    ok = 0
    for e in events:
        action = str(e.get("recommended_action") or "")
        if action in _ACTIONS:
            ok += 1
        # Heartbeat should not force review
        code = str(((e.get("trigger") or {}) if isinstance(e.get("trigger"), dict) else {}).get("code") or "")
        if code == "coverage_heartbeat" and e.get("requires_review"):
            ok -= 1
    return round(100.0 * max(0, ok) / max(1, len(events)), 2), f"ok={ok}"


def _score_latency(pack: dict[str, Any]) -> tuple[float, str]:
    # Soft proxy: pack present with timestamp / deterministic flag = timely monitoring pass
    if pack.get("timestamp") or pack.get("as_of"):
        return 95.0, "timestamped"
    if pack.get("deterministic"):
        return 85.0, "deterministic"
    return 60.0, "untimestamped"


def _score_coverage(pack: dict[str, Any], events: list[dict[str, Any]]) -> tuple[float, str]:
    covered = pack.get("domains_covered") or []
    domains = {str(d) for d in covered if d}
    if not domains:
        for e in events:
            trig = e.get("trigger") if isinstance(e.get("trigger"), dict) else {}
            if trig.get("domain"):
                domains.add(str(trig["domain"]))
    n = len(domains)
    if n >= 10:
        return 100.0, f"n={n}"
    if n >= 6:
        return 80.0, f"n={n}"
    if n >= 3:
        return 55.0, f"n={n}"
    return 25.0, f"n={n}"


def _score_explainability(events: list[dict[str, Any]]) -> tuple[float, str]:
    if not events:
        return 20.0, "no_events"
    pts = 0.0
    for e in events:
        local = 0.0
        trig = e.get("trigger") if isinstance(e.get("trigger"), dict) else {}
        if trig.get("description") or e.get("explanation"):
            local += 40.0
        if e.get("source"):
            local += 20.0
        if e.get("severity"):
            local += 20.0
        if e.get("recommended_action"):
            local += 20.0
        pts += min(100.0, local)
    return round(pts / max(1, len(events)), 2), f"n={len(events)}"


def judge_monitoring_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    _ = question
    pack = _pack(probe)
    if not pack:
        return {
            "dimension": "monitoring_quality",
            "score": None,
            "mqs": None,
            "passed": True,
            "n_a": True,
            "mqs_version": MQS_VERSION,
            "independent_of_cio": True,
            "independent_of_pqs": True,
            "root_cause": None,
            "components": {},
            "note": "No monitoring_office pack on probe",
        }

    events = _events(pack)
    scorers = {
        "trigger_relevance": lambda: _score_trigger_relevance(events),
        "false_positive_discipline": lambda: _score_false_positive(events, pack),
        "event_traceability": lambda: _score_traceability(events, pack),
        "review_recommendation_quality": lambda: _score_review_recs(events),
        "latency": lambda: _score_latency(pack),
        "monitoring_coverage": lambda: _score_coverage(pack, events),
        "explainability": lambda: _score_explainability(events),
    }
    components: dict[str, dict[str, Any]] = {}
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": MQS_COMPONENT_WEIGHTS[name]}

    mqs = 0.0
    for name, w in MQS_COMPONENT_WEIGHTS.items():
        mqs += w * float(components[name]["score"])
    mqs = round(mqs, 2)
    passed = mqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None if passed else f"mqs_weak_{worst[0]}"

    return {
        "dimension": "monitoring_quality",
        "score": mqs,
        "mqs": mqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(MQS_COMPONENT_WEIGHTS),
        "components": components,
        "portfolio_idea": pack.get("portfolio_idea"),
        "n_events": pack.get("n_events") if pack.get("n_events") is not None else len(events),
        "requires_review": pack.get("requires_review"),
        "mutates_thesis": False,
        "mqs_version": MQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "independent_of_cfqs": True,
        "independent_of_itqs": True,
        "independent_of_dqs": True,
        "independent_of_pqs": True,
        "root_cause": root,
    }


def aggregate_mqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in MQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("monitoring_quality")) or r.get("monitoring_quality") or {}
        if j.get("n_a") or (j.get("mqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("mqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in MQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    return {
        "mqs_version": MQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_mqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "note": "MQS does not affect IEL overall / CIO / prior Phase 4–5 metric weights",
    }
