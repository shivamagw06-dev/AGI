"""Research Assignment Book — every analyst receives a mission before research."""

from __future__ import annotations

from typing import Any

ASSIGNMENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "Business": {
        "mission": "Determine whether the company possesses a durable competitive advantage.",
        "required_questions": [
            "What is the source of the moat?",
            "Is it strengthening or weakening?",
            "Which evidence supports this?",
            "Which evidence contradicts this?",
            "Confidence?",
        ],
        "deliverable": "One institutional judgement.",
        "maximum_length_words": 500,
        "evidence_required": 5,
        "must_not_discuss": ["PE", "DCF", "Interest rates", "Portfolio"],
    },
    "Financial": {
        "mission": "Determine whether the financial statements support the investment thesis.",
        "required_questions": [
            "Are earnings cash-backed?",
            "Is ROIC durable?",
            "Is capital allocation value creating?",
            "Which evidence weakens this conclusion?",
        ],
        "deliverable": "Financial Opinion.",
        "maximum_length_words": 600,
        "evidence_required": 5,
        "must_not_discuss": ["Brand", "Moat", "Valuation"],
        "evidence_note": "Minimum 10 years where available.",
    },
    "Valuation": {
        "mission": "Determine whether the current valuation already discounts expected business quality.",
        "required_questions": [
            "What is priced in?",
            "What assumptions matter most?",
            "Where is the margin of safety?",
            "What would change the valuation?",
        ],
        "deliverable": "Valuation Opinion.",
        "maximum_length_words": 500,
        "evidence_required": 4,
        "must_not_discuss": ["Management quality", "Business moat"],
    },
    "Risk": {
        "mission": "Identify material risks that could invalidate the thesis.",
        "required_questions": [
            "What are the top downside risks?",
            "Which are quantifiable vs qualitative?",
            "What would force a thesis change?",
            "Confidence in risk ranking?",
        ],
        "deliverable": "Risk Opinion.",
        "maximum_length_words": 450,
        "evidence_required": 4,
        "must_not_discuss": ["Target price", "Buy rating"],
    },
    "Macro": {
        "mission": "Determine how macro and policy conditions transmit to the subject.",
        "required_questions": [
            "Which macro variables matter?",
            "What is the policy path?",
            "How does transmission work?",
            "What breaks the base case?",
        ],
        "deliverable": "Macro Opinion.",
        "maximum_length_words": 450,
        "evidence_required": 3,
        "must_not_discuss": ["Company moat", "Stock-specific PE"],
    },
    "Sector": {
        "mission": "Assess competitive position within the industry structure.",
        "required_questions": [
            "Who has structural advantage?",
            "How is industry profitability evolving?",
            "Where does the subject sit versus peers?",
        ],
        "deliverable": "Sector Opinion.",
        "maximum_length_words": 450,
        "evidence_required": 3,
        "must_not_discuss": ["Portfolio weights"],
    },
    "Forecast": {
        "mission": "Construct a coherent forward path with explicit assumptions.",
        "required_questions": [
            "What is the base path?",
            "What drives upside and downside?",
            "Which assumptions are most fragile?",
        ],
        "deliverable": "Forecast Opinion.",
        "maximum_length_words": 450,
        "evidence_required": 3,
        "must_not_discuss": ["Portfolio construction"],
    },
    "Portfolio": {
        "mission": "Judge portfolio fit, sizing, and constraint compatibility.",
        "required_questions": [
            "Does this improve risk-adjusted portfolio quality?",
            "What size is appropriate?",
            "Which constraints bind?",
        ],
        "deliverable": "Portfolio Opinion.",
        "maximum_length_words": 400,
        "evidence_required": 2,
        "must_not_discuss": ["Business moat details", "Accounting red flags"],
    },
    "Committee": {
        "mission": "Synthesise specialist opinions into a committee view.",
        "required_questions": [
            "Where do specialists agree?",
            "Where is dissent material?",
            "What is the committee stance?",
        ],
        "deliverable": "Committee Opinion.",
        "maximum_length_words": 350,
        "evidence_required": 3,
        "must_not_discuss": ["New primary research"],
    },
    "CIO": {
        "mission": "Issue the final institutional decision summary.",
        "required_questions": [
            "What is the decision?",
            "What would change it?",
            "How confident are we?",
        ],
        "deliverable": "CIO Summary.",
        "maximum_length_words": 300,
        "evidence_required": 1,
        "must_not_discuss": ["Raw data dumps"],
    },
    "Research Writer": {
        "mission": "Assemble the publication into the approved blueprint structure.",
        "required_questions": [
            "Does every mandatory section exist?",
            "Is ownership respected?",
            "Are quality rules satisfied?",
        ],
        "deliverable": "Institutional report draft.",
        "maximum_length_words": 2000,
        "evidence_required": 0,
        "must_not_discuss": ["Invented facts"],
    },
    "Academy": {
        "mission": "Teach the concept with clarity and correct institutional framing.",
        "required_questions": [
            "Is the definition precise?",
            "Is calculation correct?",
            "Are common mistakes covered?",
        ],
        "deliverable": "Educational judgement.",
        "maximum_length_words": 400,
        "evidence_required": 2,
        "must_not_discuss": ["Buy/sell recommendation", "Portfolio"],
    },
    "Accounting": {
        "mission": "Assess accounting quality and earnings integrity.",
        "required_questions": [
            "Are there red flags?",
            "Is earnings quality high?",
            "What evidence weakens confidence?",
        ],
        "deliverable": "Accounting Opinion.",
        "maximum_length_words": 450,
        "evidence_required": 4,
        "must_not_discuss": ["Brand narrative", "Target price"],
    },
    "Management": {
        "mission": "Assess management quality and capital allocation discipline.",
        "required_questions": [
            "Is capital allocation value-creating?",
            "Is communication credible?",
            "What evidence contradicts a positive view?",
        ],
        "deliverable": "Management Opinion.",
        "maximum_length_words": 450,
        "evidence_required": 3,
        "must_not_discuss": ["DCF outputs"],
    },
    "Market": {
        "mission": "Frame near-term market expectations and levels.",
        "required_questions": [
            "What is priced for the session/horizon?",
            "Which levels matter?",
            "What would surprise the market?",
        ],
        "deliverable": "Market Opinion.",
        "maximum_length_words": 300,
        "evidence_required": 2,
        "must_not_discuss": ["Long-term moat theory"],
    },
    "News": {
        "mission": "Distil material news and its research implications.",
        "required_questions": [
            "What changed?",
            "Is it thesis-relevant?",
            "What should specialists revisit?",
        ],
        "deliverable": "News Opinion.",
        "maximum_length_words": 250,
        "evidence_required": 2,
        "must_not_discuss": ["Full valuation rebuild"],
    },
}


def build_assignment_book(
    *,
    question: str,
    report_type: str,
    section_order: list[str],
    section_owner: dict[str, str],
    priorities: dict[str, str],
) -> dict[str, Any]:
    # Owners with at least one non-suppressed, non-hidden section
    active_owners: dict[str, list[str]] = {}
    for key in section_order:
        pri = priorities.get(key)
        if pri in {"suppressed", "hidden"}:
            continue
        owner = section_owner.get(key)
        if not owner:
            continue
        active_owners.setdefault(owner, []).append(key)

    assignments = []
    for owner, sections in active_owners.items():
        tmpl = ASSIGNMENT_TEMPLATES.get(owner) or {
            "mission": f"Own institutional sections: {', '.join(sections)}.",
            "required_questions": ["What is the institutional judgement?", "Confidence?"],
            "deliverable": "Section judgement.",
            "maximum_length_words": 400,
            "evidence_required": 2,
            "must_not_discuss": ["Out-of-mandate topics"],
        }
        assignments.append(
            {
                "owner": owner,
                "mission": tmpl["mission"],
                "required_questions": list(tmpl["required_questions"]),
                "deliverable": tmpl["deliverable"],
                "maximum_length_words": tmpl["maximum_length_words"],
                "evidence_required": tmpl["evidence_required"],
                "evidence_note": tmpl.get("evidence_note"),
                "must_not_discuss": list(tmpl["must_not_discuss"]),
                "assigned_sections": sections,
                "report_type": report_type,
                "research_question": question,
            }
        )

    return {
        "enabled": True,
        "assignment_count": len(assignments),
        "assignments": assignments,
        "law": "Every participant has a defined mandate before reasoning begins.",
    }
