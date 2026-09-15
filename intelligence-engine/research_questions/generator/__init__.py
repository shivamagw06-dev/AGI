"""Research question generator — 10–30 institutional questions per hypothesis."""

from __future__ import annotations

from typing import Any

from research_questions.quality_rules import enforce_quality
from research_questions.question_library import templates_for_hypothesis_type
from research_questions.schema import MAX_QUESTIONS_PER_HYPOTHESIS, MIN_QUESTIONS_PER_HYPOTHESIS


def _entity_label(entity: dict[str, Any] | None, ask_question: str) -> str:
    ent = entity or {}
    name = str(ent.get("canonical_name") or ent.get("name") or ent.get("ticker") or "").strip()
    if name:
        return name
    q = (ask_question or "").strip()
    for prefix in ("Should I buy ", "Should I sell ", "What are the risks in ", "Analyse ", "Analyze "):
        if q.startswith(prefix):
            return q[len(prefix) :].rstrip("?").strip() or "the subject"
    if "nifty" in q.lower():
        return "Nifty IT" if "it" in q.lower() else "the index"
    return "the subject"


def _peer_label(entity: dict[str, Any] | None, ask_question: str) -> str:
    ent = entity or {}
    peers = ent.get("peers") or []
    if peers:
        p0 = peers[0]
        if isinstance(p0, dict):
            return str(p0.get("canonical_name") or p0.get("ticker") or "peers")
        return str(p0)
    q = (ask_question or "").lower()
    if " vs " in q:
        parts = ask_question.replace("?", "").split(" vs ")
        if len(parts) >= 2:
            return parts[1].strip()
    name = _entity_label(entity, ask_question).lower()
    if "bank" in name or "hdfc" in name or "icici" in name:
        return "ICICI Bank and Axis Bank"
    if "infosys" in name or "tcs" in name or "wipro" in name or "nifty" in name:
        return "Infosys / TCS peer set"
    return "closest listed peers"


def _render(template: dict[str, Any], *, entity: str, peer: str) -> dict[str, Any]:
    text = str(template["question"]).format(entity=entity, peer=peer)
    return {
        "question": text,
        "type": template["type"],
        "priority": template["priority"],
        "required_evidence": list(template.get("evidence") or []),
        "decision_impact": int(template.get("impact") or 5),
        "tree_layer": template.get("tree_layer"),
        "depends_on_layers": list(template.get("depends_on_layers") or []),
        "status": "Waiting",
    }


def generate_for_hypothesis(
    hypothesis: dict[str, Any],
    *,
    ask_question: str,
    entity: dict[str, Any] | None = None,
    index: int = 1,
) -> list[dict[str, Any]]:
    """Generate a quality-filtered question set for one hypothesis."""
    hyp_type = str(hypothesis.get("type") or "Business")
    hyp_id = str(hypothesis.get("id") or f"H{index}")
    entity_name = _entity_label(entity, ask_question)
    peer = _peer_label(entity, ask_question)

    templates = templates_for_hypothesis_type(hyp_type)
    # Extra fillers to guarantee minima / depth without generics
    fillers = [
        {
            "question": f"Has the core metric underlying this hypothesis for {entity_name} deteriorated versus {peer} in the last eight quarters?",
            "type": "Verification",
            "priority": "Important",
            "evidence": ["FIL", "PIL"],
            "impact": 8,
            "tree_layer": "Peer",
            "depends_on_layers": ["Historical"],
        },
        {
            "question": f"What historical analogue best stress-tests this hypothesis for {entity_name}?",
            "type": "Historical",
            "priority": "Supporting",
            "evidence": ["Historical"],
            "impact": 6,
            "tree_layer": "Historical",
            "depends_on_layers": [],
        },
        {
            "question": f"If {peer} closes the gap on the key metric, does the valuation premium for {entity_name} remain justified?",
            "type": "Contradiction",
            "priority": "Important",
            "evidence": ["PIL", "Valuation"],
            "impact": 8,
            "tree_layer": "Valuation",
            "depends_on_layers": ["Peer"],
        },
        {
            "question": f"Which leading indicator would show this hypothesis failing for {entity_name} before earnings do?",
            "type": "Forecast",
            "priority": "Important",
            "evidence": ["Forecast", "Risk"],
            "impact": 7,
            "tree_layer": "Forecast",
            "depends_on_layers": ["Valuation"],
        },
        {
            "question": f"Are accounting or disclosure choices masking the true trend for {entity_name} on this thesis?",
            "type": "Accounting",
            "priority": "Supporting",
            "evidence": ["Accounting", "FIL"],
            "impact": 5,
            "tree_layer": "Historical",
            "depends_on_layers": [],
        },
        {
            "question": f"How does this hypothesis change position sizing for {entity_name} inside a diversified portfolio?",
            "type": "Portfolio",
            "priority": "Optional",
            "evidence": ["Portfolio"],
            "impact": 3,
            "tree_layer": "Forecast",
            "depends_on_layers": ["Valuation"],
        },
    ]

    raw_templates = list(templates) + fillers
    questions: list[dict[str, Any]] = []
    seen_texts: list[str] = []

    for tmpl in raw_templates:
        if len(questions) >= MAX_QUESTIONS_PER_HYPOTHESIS:
            break
        row = _render(tmpl, entity=entity_name, peer=peer)
        row["hypothesis_id"] = hyp_id
        row["hypothesis"] = hypothesis.get("statement") or hypothesis.get("hypothesis")
        checked = enforce_quality(row, existing_questions=seen_texts)
        if not checked.get("quality_compliant"):
            continue
        seen_texts.append(str(checked["question"]))
        questions.append(checked)

    # If still short on minima, add tightly-scoped extras
    extra_idx = 1
    while len(questions) < MIN_QUESTIONS_PER_HYPOTHESIS and extra_idx <= 12:
        extra = {
            "question": (
                f"Relative to {peer}, has the decision-critical metric for this hypothesis on "
                f"{entity_name} improved or worsened over the last {extra_idx + 2} years?"
            ),
            "type": "Peer" if extra_idx % 2 else "Historical",
            "priority": "Supporting",
            "required_evidence": ["PIL", "Historical"],
            "decision_impact": 6,
            "tree_layer": "Peer" if extra_idx % 2 else "Historical",
            "depends_on_layers": ["Historical"] if extra_idx % 2 else [],
            "status": "Waiting",
            "hypothesis_id": hyp_id,
            "hypothesis": hypothesis.get("statement") or hypothesis.get("hypothesis"),
        }
        # Ensure contradiction floor
        contra = sum(1 for q in questions if q.get("type") == "Contradiction")
        hist = sum(1 for q in questions if q.get("type") == "Historical")
        peer_n = sum(1 for q in questions if q.get("type") == "Peer")
        if contra < 3:
            extra.update(
                {
                    "question": (
                        f"What specific disconfirming evidence would force rejection of this hypothesis "
                        f"for {entity_name} in scenario {extra_idx}?"
                    ),
                    "type": "Contradiction",
                    "priority": "Critical",
                    "required_evidence": ["Risk", "FIL"],
                    "decision_impact": 9,
                    "tree_layer": "Forecast",
                }
            )
        elif hist < 2:
            extra.update(
                {
                    "question": (
                        f"In prior cycles, did {entity_name} exhibit the same pattern assumed by this "
                        f"hypothesis when conditions resembled scenario {extra_idx}?"
                    ),
                    "type": "Historical",
                    "priority": "Important",
                    "required_evidence": ["Historical"],
                    "decision_impact": 7,
                    "tree_layer": "Historical",
                }
            )
        elif peer_n < 2:
            extra.update(
                {
                    "question": (
                        f"Versus {peer}, is {entity_name} still ahead on the hypothesis metric in the "
                        f"latest comparable period (window {extra_idx})?"
                    ),
                    "type": "Peer",
                    "priority": "Important",
                    "required_evidence": ["PIL"],
                    "decision_impact": 8,
                    "tree_layer": "Peer",
                }
            )
        checked = enforce_quality(extra, existing_questions=seen_texts)
        extra_idx += 1
        if not checked.get("quality_compliant"):
            continue
        seen_texts.append(str(checked["question"]))
        questions.append(checked)

    # Number questions
    for i, q in enumerate(questions, start=1):
        q["id"] = f"{hyp_id}-Q{i}"
    return questions


def generate_question_sets(
    *,
    ask_question: str,
    hypotheses: list[dict[str, Any]],
    entity: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    blocks = []
    for i, hyp in enumerate(hypotheses, start=1):
        qs = generate_for_hypothesis(hyp, ask_question=ask_question, entity=entity, index=i)
        blocks.append(
            {
                "hypothesis_id": hyp.get("id") or f"H{i}",
                "hypothesis": hyp.get("statement") or hyp.get("hypothesis"),
                "hypothesis_type": hyp.get("type"),
                "hypothesis_confidence": hyp.get("confidence"),
                "research_questions": qs,
                "question_count": len(qs),
            }
        )
    return blocks
