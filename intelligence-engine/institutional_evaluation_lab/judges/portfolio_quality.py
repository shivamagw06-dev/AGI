"""Portfolio Quality Score (PQS) — independent IEL metric for AGI v4.0 Sprint 5.3.

Does NOT change CIO / HQS / CQS / CFQS / ITQS / DQS weights.

Components:
  Relative ranking quality · Role assignment · Diversification ·
  Constraint compliance · Monitoring · Decision consistency ·
  Portfolio explainability

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

PQS_VERSION = "pqs-v1.0.0"

PQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "relative_ranking_quality": 0.18,
    "role_assignment": 0.14,
    "diversification": 0.12,
    "constraint_compliance": 0.16,
    "monitoring": 0.12,
    "decision_consistency": 0.14,
    "portfolio_explainability": 0.14,
}

_ROLES = {
    "Core Compounder",
    "Defensive",
    "Cyclical",
    "Turnaround",
    "Event Driven",
    "Income",
    "Macro Hedge",
    "Cash Alternative",
    "Satellite",
}


def _pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("portfolio_office") or {})


def _idea(pack: dict[str, Any]) -> dict[str, Any]:
    return dict(pack.get("idea") or {})


def _score_ranking(idea: dict[str, Any], pack: dict[str, Any]) -> tuple[float, str]:
    rank = idea.get("relative_rank")
    peers = pack.get("peer_ranking") or idea.get("peer_ranking") or []
    if rank is None and not peers:
        return 40.0, "no_rank_yet"
    score = 70.0
    if rank is not None and int(rank) >= 1:
        score += 15.0
    if peers:
        score += 15.0
    return min(100.0, score), f"rank={rank},peers={len(peers)}"


def _score_role(idea: dict[str, Any]) -> tuple[float, str]:
    role = str(idea.get("expected_role") or "")
    if role in _ROLES:
        return 100.0, role
    if role:
        return 40.0, f"unknown:{role}"
    return 0.0, "missing"


def _score_diversification(idea: dict[str, Any]) -> tuple[float, str]:
    if idea.get("sector") and idea.get("theme"):
        return 90.0, f"{idea.get('sector')}/{idea.get('theme')}"
    if idea.get("sector"):
        return 60.0, "sector_only"
    return 30.0, "missing_sector"


def _score_constraints(idea: dict[str, Any], pack: dict[str, Any]) -> tuple[float, str]:
    if idea.get("position") is not None or idea.get("position_size") is not None:
        return 0.0, "position_present"
    if pack.get("positions_emitted") or pack.get("orders_emitted"):
        return 0.0, "positions_or_orders"
    check = idea.get("constraint_check") or {}
    pols = check.get("policies") or {}
    if pols.get("allow_positions") or pols.get("allow_execution"):
        return 20.0, "policy_allows_forbidden"
    if check.get("compliant") is True:
        return 100.0, "compliant"
    if check.get("violations"):
        return 55.0, f"violations={check.get('violations')}"
    return 70.0, "no_check"


def _score_monitoring(idea: dict[str, Any]) -> tuple[float, str]:
    m = idea.get("monitoring") or []
    if not m:
        return 30.0, "empty"
    return min(100.0, 50.0 + 10.0 * min(5, len(m))), f"n={len(m)}"


def _score_decision_consistency(idea: dict[str, Any], probe: dict[str, Any]) -> tuple[float, str]:
    dec = str(idea.get("decision") or "")
    ido = ((probe.get("decision_office") or {}).get("decision") or {})
    if ido and dec and dec != str(ido.get("decision") or ""):
        return 40.0, "mismatched_decision"
    if idea.get("decision_id") and idea.get("investment_thesis_id"):
        return 100.0, "linked"
    if idea.get("investment_thesis_id"):
        return 70.0, "thesis_only"
    return 40.0, "weak_links"


def _score_explainability(idea: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    notes = []
    for key, pts in (
        ("investment_view", 25),
        ("expected_role", 20),
        ("correlation", 20),
        ("conviction", 15),
        ("risk_budget", 10),
        ("capacity", 10),
    ):
        if idea.get(key) not in (None, ""):
            score += pts
            notes.append(key)
    return min(100.0, score), ",".join(notes) or "none"


def judge_portfolio_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    _ = question
    pack = _pack(probe)
    if not pack:
        return {
            "dimension": "portfolio_quality",
            "score": None,
            "pqs": None,
            "passed": True,
            "n_a": True,
            "pqs_version": PQS_VERSION,
            "independent_of_cio": True,
            "independent_of_dqs": True,
            "root_cause": None,
            "components": {},
            "note": "No portfolio_office pack on probe",
        }

    idea = _idea(pack)
    scorers = {
        "relative_ranking_quality": lambda: _score_ranking(idea, pack),
        "role_assignment": lambda: _score_role(idea),
        "diversification": lambda: _score_diversification(idea),
        "constraint_compliance": lambda: _score_constraints(idea, pack),
        "monitoring": lambda: _score_monitoring(idea),
        "decision_consistency": lambda: _score_decision_consistency(idea, probe),
        "portfolio_explainability": lambda: _score_explainability(idea),
    }
    components: dict[str, dict[str, Any]] = {}
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": PQS_COMPONENT_WEIGHTS[name]}

    pqs = 0.0
    for name, w in PQS_COMPONENT_WEIGHTS.items():
        pqs += w * float(components[name]["score"])
    pqs = round(pqs, 2)
    passed = pqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None if passed else f"pqs_weak_{worst[0]}"

    return {
        "dimension": "portfolio_quality",
        "score": pqs,
        "pqs": pqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(PQS_COMPONENT_WEIGHTS),
        "components": components,
        "idea_id": idea.get("idea_id"),
        "relative_rank": idea.get("relative_rank"),
        "expected_role": idea.get("expected_role"),
        "positions_emitted": False,
        "pqs_version": PQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "independent_of_cfqs": True,
        "independent_of_itqs": True,
        "independent_of_dqs": True,
        "root_cause": root,
    }


def aggregate_pqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in PQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("portfolio_quality")) or r.get("portfolio_quality") or {}
        if j.get("n_a") or (j.get("pqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("pqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in PQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    return {
        "pqs_version": PQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_pqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "note": "PQS does not affect IEL overall / CIO / prior Phase 4–5 metric weights",
    }
