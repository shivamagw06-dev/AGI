"""Evidence traceability — conclusion back to hypothesis, question, evidence and source."""

from __future__ import annotations

from typing import Any


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_evidence_trace(trace: dict[str, Any]) -> dict[str, Any]:
    data = trace["stage_data"]
    hypotheses_pkg = data.get("Hypothesis") or {}
    questions_pkg = data.get("Research Questions") or {}
    testing_pkg = data.get("Testing") or {}
    belief_pkg = data.get("Belief Update") or {}
    thesis = data.get("Investment Thesis") or {}
    debate = data.get("Debate") or {}
    decision = data.get("Decision Readiness") or {}

    hypotheses = _list(hypotheses_pkg.get("hypotheses"))
    if not hypotheses:
        hypotheses = _list(testing_pkg.get("tested_hypotheses"))
    tested = _list(testing_pkg.get("tested_hypotheses"))
    beliefs = _list(belief_pkg.get("beliefs"))
    question_sets = _list(questions_pkg.get("hypothesis_question_sets"))
    flat_questions = _list(questions_pkg.get("research_questions"))

    by_hypothesis: dict[str, dict[str, Any]] = {}
    for index, hypothesis in enumerate(hypotheses, start=1):
        if not isinstance(hypothesis, dict):
            continue
        hid = str(
            hypothesis.get("id")
            or hypothesis.get("hypothesis_id")
            or f"H{index}"
        )
        by_hypothesis[hid] = hypothesis

    questions_by_hypothesis: dict[str, list[dict[str, Any]]] = {}
    for block in question_sets:
        if isinstance(block, dict):
            questions_by_hypothesis[str(block.get("hypothesis_id"))] = [
                q for q in _list(block.get("research_questions")) if isinstance(q, dict)
            ]
    for question in flat_questions:
        if isinstance(question, dict):
            questions_by_hypothesis.setdefault(
                str(question.get("hypothesis_id") or "H1"), []
            ).append(question)

    evidence_by_hypothesis: dict[str, list[dict[str, Any]]] = {}
    for hypothesis in tested:
        if not isinstance(hypothesis, dict):
            continue
        hid = str(hypothesis.get("id") or hypothesis.get("hypothesis_id") or "H1")
        evidence_by_hypothesis[hid] = (
            _list(hypothesis.get("evidence_effects"))
            + _list(hypothesis.get("supporting_evidence"))
            + _list(hypothesis.get("contradicting_evidence"))
        )

    conclusions = []
    for belief in beliefs:
        if isinstance(belief, dict):
            conclusions.append(
                {
                    "id": f"BELIEF::{belief.get('hypothesis_id') or belief.get('id')}",
                    "type": "Belief",
                    "text": belief.get("hypothesis"),
                    "hypothesis_id": str(
                        belief.get("hypothesis_id") or belief.get("id") or "H1"
                    ),
                }
            )
    core = thesis.get("core_thesis")
    core_text = core.get("statement") if isinstance(core, dict) else core
    if core_text:
        conclusions.append(
            {
                "id": "THESIS::CORE",
                "type": "Investment Thesis",
                "text": core_text,
                "hypothesis_id": next(iter(by_hypothesis), "H1"),
            }
        )
    consensus = debate.get("consensus") or {}
    if consensus:
        conclusions.append(
            {
                "id": "DEBATE::CONSENSUS",
                "type": "Debate Consensus",
                "text": f"{consensus.get('state')} ({consensus.get('agreement_pct')}% agreement)",
                "hypothesis_id": next(iter(by_hypothesis), "H1"),
            }
        )
    decision_status = (
        decision.get("decision_status")
        or (decision.get("decision_readiness") or {}).get("status")
    )
    if decision_status:
        conclusions.append(
            {
                "id": "DECISION::READINESS",
                "type": "Decision Readiness",
                "text": str(decision_status),
                "hypothesis_id": next(iter(by_hypothesis), "H1"),
            }
        )

    traces = []
    orphans = []
    for conclusion in conclusions:
        hid = conclusion["hypothesis_id"]
        hypothesis = by_hypothesis.get(hid)
        if not hypothesis and by_hypothesis:
            hid, hypothesis = next(iter(by_hypothesis.items()))
        questions = questions_by_hypothesis.get(hid) or flat_questions[:3]
        evidence = evidence_by_hypothesis.get(hid) or [
            item
            for tested_hypothesis in tested[:1]
            for item in _list(tested_hypothesis.get("evidence_effects"))
        ]
        evidence_rows = []
        for index, item in enumerate(evidence[:8], start=1):
            if not isinstance(item, dict):
                item = {"text": str(item)}
            evidence_rows.append(
                {
                    "evidence_id": item.get("id") or f"{hid}-E{index}",
                    "text": item.get("text") or item.get("statement"),
                    "source": (
                        item.get("source")
                        or item.get("kind")
                        or "hypothesis_testing"
                    ),
                    "effect": item.get("effect"),
                }
            )
        complete = bool(hypothesis and questions and evidence_rows)
        row = {
            "conclusion_id": conclusion["id"],
            "conclusion_type": conclusion["type"],
            "conclusion": conclusion["text"],
            "hypothesis_id": hid if hypothesis else None,
            "hypothesis": (
                hypothesis.get("hypothesis")
                or hypothesis.get("statement")
                if hypothesis
                else None
            ),
            "research_question_ids": [
                q.get("id") for q in questions[:6] if isinstance(q, dict)
            ],
            "evidence": evidence_rows,
            "reasoning_steps": [
                "Hypothesis generated",
                "Research questions assigned",
                "Evidence attributed",
                "Hypothesis tested and challenged",
                "Belief updated",
                f"{conclusion['type']} produced",
            ],
            "complete": complete,
        }
        traces.append(row)
        if not complete:
            orphans.append(
                {
                    "conclusion_id": conclusion["id"],
                    "missing": [
                        label
                        for label, present in {
                            "hypothesis": bool(hypothesis),
                            "research_questions": bool(questions),
                            "evidence": bool(evidence_rows),
                        }.items()
                        if not present
                    ],
                }
            )
    traceability = (
        sum(1 for row in traces if row["complete"]) / len(traces)
        if traces
        else 0.0
    )
    return {
        "conclusion_traces": traces,
        "conclusion_count": len(traces),
        "traceable_count": sum(1 for row in traces if row["complete"]),
        "traceability": round(traceability, 4),
        "traceability_pct": round(traceability * 100),
        "orphan_conclusions": orphans,
        "orphan_count": len(orphans),
        "passed": traceability == 1.0 and not orphans,
    }
