"""Reasoning trace — the unbroken question-to-decision chain."""

from __future__ import annotations

from typing import Any

from reasoning_audit.schema import REASONING_STAGES


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _unwrap(payload: dict[str, Any], key: str) -> dict[str, Any]:
    wrapper = _dict(payload.get(key))
    return _dict(wrapper.get(key)) or wrapper


def _count_items(stage: str, data: dict[str, Any]) -> int:
    fields = {
        "Hypothesis": ("hypotheses", "tested_hypotheses", "beliefs"),
        "Research Questions": ("research_questions", "hypothesis_question_sets"),
        "Evidence": ("evidence", "evidence_effects", "supporting_evidence"),
        "Testing": ("tested_hypotheses",),
        "Falsification": ("reports", "falsification_reports", "hypotheses"),
        "Belief Update": ("beliefs",),
        "Investment Thesis": ("supporting_pillars", "catalysts"),
        "Debate": ("analyst_positions", "evidence_conflicts"),
        "Decision Readiness": ("decision_heat_map", "conditions"),
    }
    for field in fields.get(stage, ()):
        value = data.get(field)
        if isinstance(value, list):
            return len(value)
    return 1 if data else 0


def build_trace(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    hypothesis = _unwrap(payload, "hypothesis_engine")
    research_questions = _unwrap(payload, "research_questions")
    testing = _unwrap(payload, "hypothesis_testing")
    falsification = (
        _unwrap(payload, "falsification_engine")
        or _unwrap(payload, "falsification")
    )
    belief = _unwrap(payload, "belief_engine")
    thesis = _unwrap(payload, "thesis_engine")
    debate = _unwrap(payload, "debate_engine")
    decision = _unwrap(payload, "decision_readiness")
    evidence = (
        _unwrap(payload, "evidence")
        or _dict(payload.get("collected_evidence"))
        or _dict(payload.get("evidence_plan"))
    )
    # Evidence is also represented by the test package's attributed effects.
    if not evidence and (
        testing.get("tested_hypotheses")
        or testing.get("hypothesis_matrix")
    ):
        evidence = {
            "source": "hypothesis_testing",
            "evidence_effects": [
                item
                for hypothesis_row in testing.get("tested_hypotheses", [])
                for item in hypothesis_row.get("evidence_effects", [])
            ],
        }

    stage_data = {
        "Question": {"question": question} if question else {},
        "Hypothesis": hypothesis,
        "Research Questions": research_questions,
        "Evidence": evidence,
        "Testing": testing,
        "Falsification": falsification,
        "Belief Update": belief,
        "Investment Thesis": (
            _dict(thesis.get("thesis"))
            or _dict(thesis.get("institutional_investment_thesis"))
            or thesis
        ),
        "Debate": (
            _dict(debate.get("debate"))
            or _dict(debate.get("institutional_debate_package"))
            or debate
        ),
        "Decision Readiness": (
            _dict(decision.get("decision_package"))
            or _dict(decision.get("institutional_decision_package"))
            or decision
        ),
    }
    nodes = []
    for idx, stage in enumerate(REASONING_STAGES[:-1], start=1):
        data = stage_data.get(stage) or {}
        nodes.append(
            {
                "id": f"TRACE-{idx:02d}",
                "stage": stage,
                "present": bool(data),
                "item_count": _count_items(stage, data),
                "source_package": {
                    "Hypothesis": "hypothesis_engine",
                    "Research Questions": "research_questions",
                    "Evidence": "evidence / hypothesis_testing",
                    "Testing": "hypothesis_testing",
                    "Falsification": "falsification_engine",
                    "Belief Update": "belief_engine",
                    "Investment Thesis": "thesis_engine",
                    "Debate": "debate_engine",
                    "Decision Readiness": "decision_readiness",
                    "Question": "request",
                }[stage],
                "summary": _summary(stage, data, question),
            }
        )
    edges = [
        {
            "from": nodes[i]["id"],
            "to": nodes[i + 1]["id"],
            "relation": "reasoning_precedes",
            "valid": nodes[i]["present"] and nodes[i + 1]["present"],
        }
        for i in range(len(nodes) - 1)
    ]
    present = sum(1 for node in nodes if node["present"])
    completeness = present / len(nodes)
    missing = [node["stage"] for node in nodes if not node["present"]]
    return {
        "nodes": nodes,
        "edges": edges,
        "stage_data": stage_data,
        "completeness": round(completeness, 4),
        "completeness_pct": round(completeness * 100),
        "missing_stages": missing,
        "unbroken": not missing and all(edge["valid"] for edge in edges),
        "chain": " → ".join(node["stage"] for node in nodes)
        + " → Reasoning Audit",
    }


def _summary(stage: str, data: dict[str, Any], question: str) -> str:
    if stage == "Question":
        return question
    fields = {
        "Hypothesis": ("hypothesis_count", "hypotheses"),
        "Research Questions": ("research_question_count", "research_questions"),
        "Testing": ("tested_count", "tested_hypotheses"),
        "Falsification": ("status", "reports"),
        "Belief Update": ("belief_count", "beliefs"),
        "Investment Thesis": ("status", "core_thesis"),
        "Debate": ("consensus", "analyst_positions"),
        "Decision Readiness": ("decision_status", "executive_summary"),
        "Evidence": ("evidence_count", "evidence_effects"),
    }
    for field in fields.get(stage, ()):
        value = data.get(field)
        if value is not None:
            if isinstance(value, list):
                return f"{len(value)} {field.replace('_', ' ')}"
            if isinstance(value, dict):
                return str(
                    value.get("statement")
                    or value.get("state")
                    or value.get("status")
                    or field
                )
            return str(value)
    return f"{stage} package present" if data else f"{stage} missing"
