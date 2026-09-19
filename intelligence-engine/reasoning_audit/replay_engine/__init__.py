"""Reasoning Replay Engine — deterministic step-by-step reconstruction."""

from __future__ import annotations

import hashlib
from typing import Any


def build_replay(
    question: str,
    trace: dict[str, Any],
    *,
    audit_status: str,
    reasoning_score: float,
) -> dict[str, Any]:
    data = trace["stage_data"]
    events = []

    def add(stage: str, title: str, detail: str, before=None, after=None):
        events.append(
            {
                "sequence": len(events) + 1,
                "stage": stage,
                "title": title,
                "detail": detail,
                "before": before,
                "after": after,
                "changed": before is not None and after is not None and before != after,
            }
        )

    add("Question", "Research question received", question)
    hypotheses = (data.get("Hypothesis") or {}).get("hypotheses") or []
    add(
        "Hypothesis",
        f"{len(hypotheses)} hypotheses generated",
        str((hypotheses[0] if hypotheses else {}).get("hypothesis") or "Hypothesis package created"),
    )
    research = data.get("Research Questions") or {}
    questions = research.get("research_questions") or []
    add(
        "Research Questions",
        f"{len(questions)} research questions created",
        "Questions assigned to evidence and analyst owners",
    )
    testing = data.get("Testing") or {}
    tested = testing.get("tested_hypotheses") or []
    evidence_count = sum(
        len(h.get("evidence_effects") or []) for h in tested
    )
    add(
        "Evidence",
        f"{evidence_count} evidence effects attributed",
        "Supporting, contradicting and neutral evidence mapped",
    )
    first_test = tested[0] if tested else {}
    add(
        "Testing",
        "Hypothesis probability tested",
        str(first_test.get("status") or "Testing completed"),
        first_test.get("initial_confidence"),
        first_test.get("updated_probability"),
    )
    falsification = data.get("Falsification") or {}
    add(
        "Falsification",
        "Falsification challenge applied",
        str(
            falsification.get("status")
            or falsification.get("summary")
            or "Falsification package completed"
        ),
        falsification.get("before_probability"),
        falsification.get("after_probability"),
    )
    belief_pkg = data.get("Belief Update") or {}
    beliefs = belief_pkg.get("beliefs") or []
    belief = beliefs[0] if beliefs else {}
    add(
        "Belief Update",
        "Bayesian belief updated",
        str(belief.get("belief_state") or "Belief package updated"),
        belief.get("prior_belief"),
        belief.get("posterior_belief"),
    )
    thesis = data.get("Investment Thesis") or {}
    core = thesis.get("core_thesis") or {}
    add(
        "Investment Thesis",
        "Institutional thesis constructed",
        str(core.get("statement") if isinstance(core, dict) else core),
        None,
        (thesis.get("conviction") or {}).get("overall"),
    )
    debate = data.get("Debate") or {}
    tournament = debate.get("challenge_tournament") or {}
    consensus = debate.get("consensus") or {}
    add(
        "Debate",
        f"Challenge Tournament completed ({tournament.get('round_count', 0)} rounds)",
        f"{tournament.get('revision_count', 0)} positions revised; consensus {consensus.get('state')}",
        None,
        consensus.get("agreement"),
    )
    decision = data.get("Decision Readiness") or {}
    decision_status = decision.get("decision_status") or (
        decision.get("decision_readiness") or {}
    ).get("status")
    readiness_score = decision.get("readiness_score") or (
        decision.get("decision_readiness") or {}
    ).get("score")
    add(
        "Decision Readiness",
        f"Decision readiness: {decision_status}",
        f"Readiness score {round(float(readiness_score or 0) * 100)}%",
        None,
        readiness_score,
    )
    add(
        "Reasoning Audit",
        f"Reasoning Audit: {audit_status}",
        f"Institutional reasoning score {round(reasoning_score * 100)}%",
        None,
        reasoning_score,
    )
    raw = "|".join(
        f"{event['stage']}:{event['title']}:{event.get('after')}"
        for event in events
    )
    return {
        "events": events,
        "event_count": len(events),
        "replayable": True,
        "controls": {
            "play": True,
            "pause": True,
            "step_forward": True,
            "step_back": True,
            "restart": True,
        },
        "estimated_duration_seconds": len(events) * 3,
        "replay_id": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
        "training_uses": [
            "debugging",
            "analyst training",
            "user explanation",
            "ILM outcome learning",
            "IRS regression diagnosis",
        ],
    }
