"""Question taxonomy — 500 labeled institutional questions for QUE training/evaluation."""

from __future__ import annotations

from typing import Any

from question_understanding_engine.resolver import understand_question
from question_understanding_engine.schema import (
    DOMAIN_DECISION_MAP,
    RESEARCH_OBJECTIVES,
    RESPONSE_STRUCTURE_BY_DECISION,
    TARGET_TAXONOMY_COUNT,
)

# Spec acceptance exemplars
_CORE_EXEMPLARS: tuple[dict[str, str], ...] = (
    {
        "literal_question": "Should I buy TCS?",
        "investor_meaning": "Should I allocate capital to TCS instead of another opportunity?",
        "decision_type": "Capital Allocation",
        "research_objective": "Determine whether expected return justifies risk.",
        "expected_deliverable": "Investment assessment clarity",
    },
    {
        "literal_question": "Does TCS deserve research?",
        "investor_meaning": "Should analyst resources be allocated?",
        "decision_type": "Research Priority",
        "research_objective": "Determine whether additional work could change investment conclusions.",
        "expected_deliverable": "Research prioritization rationale",
    },
    {
        "literal_question": "Compare Infosys and TCS.",
        "investor_meaning": "If I only invest in one company, which differences matter?",
        "decision_type": "Peer Selection",
        "research_objective": "Identify investment-relevant differences.",
        "expected_deliverable": "Investment-relevant peer differences",
    },
    {
        "literal_question": "Why is Titan expensive?",
        "investor_meaning": "What expectations are embedded in today's valuation?",
        "decision_type": "Valuation Assessment",
        "research_objective": "Determine what expectations are embedded in price and whether they are justified.",
        "expected_deliverable": "Expectations embedded in price",
    },
    {
        "literal_question": "Why did the stock fall?",
        "investor_meaning": "Did the investment thesis change?",
        "decision_type": "Thesis Validation",
        "research_objective": "Determine whether the investment thesis still holds.",
        "expected_deliverable": "Thesis validation summary",
    },
)

# Common investor phrasings for expansion
_PHRASING_VARIANTS: tuple[tuple[str, str], ...] = (
    ("Should I invest in {company}?", "Capital Allocation"),
    ("Is {company} a good investment?", "Capital Allocation"),
    ("What is the investment case for {company}?", "Capital Allocation"),
    ("Is {company} worth buying at current levels?", "Capital Allocation"),
    ("Should I add {company} to my portfolio?", "Portfolio Construction"),
    ("How does {company} fit my portfolio?", "Portfolio Construction"),
    ("What are the risks in {company}?", "Risk Assessment"),
    ("What could go wrong with {company}?", "Risk Assessment"),
    ("How should I monitor {company}?", "Monitoring"),
    ("What KPIs matter for {company}?", "Monitoring"),
    ("Explain {company} valuation.", "Valuation Assessment"),
    ("Is {company} overvalued?", "Valuation Assessment"),
    ("How does {company} compare to peers?", "Peer Selection"),
    ("{company} vs Infosys — which is better?", "Peer Selection"),
    ("How does {company} make money?", "Business Understanding"),
    ("Does {company} have a moat?", "Business Understanding"),
    ("What changed after {company} earnings?", "Earnings Review"),
    ("How do rates affect {company}?", "Macro Impact"),
    ("What is the outlook for {company}'s sector?", "Sector Allocation"),
    ("Why is {company} interesting?", "Idea Generation"),
)

_COMPANIES: tuple[tuple[str, str], ...] = (
    ("TCS", "Tata Consultancy Services"),
    ("INFY", "Infosys"),
    ("HDFCBANK", "HDFC Bank"),
    ("ICICIBANK", "ICICI Bank"),
    ("RELIANCE", "Reliance Industries"),
    ("TITAN", "Titan"),
    ("ASIANPAINT", "Asian Paints"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("LT", "Larsen & Toubro"),
    ("MARUTI", "Maruti Suzuki"),
)


def _from_iic() -> list[dict[str, Any]]:
    try:
        from institutional_investor_curriculum.domains import UNIVERSAL_QUESTIONS
        from institutional_investor_curriculum.schema import ANCHOR_COMPANIES, DOMAIN_EDITORIAL_OBJECTIVES
    except ImportError:
        return []

    items: list[dict[str, Any]] = []
    for uq in UNIVERSAL_QUESTIONS:
        domain = uq["domain"]
        decision = DOMAIN_DECISION_MAP.get(domain, "Business Understanding")
        for ticker, company in ANCHOR_COMPANIES[:5]:
            literal = uq["template"].format(company=company)
            understood = understand_question(literal, ticker=ticker, company=company, domain=domain)
            items.append({
                "id": f"QT_{len(items)+1:04d}",
                "literal_question": literal,
                "investor_meaning": understood["investor_meaning"],
                "decision_type": decision,
                "research_objective": RESEARCH_OBJECTIVES.get(decision, understood["research_objective"]),
                "expected_deliverable": understood["expected_deliverable"],
                "correct_response_structure": RESPONSE_STRUCTURE_BY_DECISION.get(decision, ""),
                "editorial_notes": DOMAIN_EDITORIAL_OBJECTIVES.get(domain, ""),
                "domain": domain,
                "ticker": ticker,
                "source": "iic_curriculum",
            })
            if len(items) >= TARGET_TAXONOMY_COUNT:
                return items
    return items


def _build_taxonomy() -> tuple[dict[str, Any], ...]:
    items: list[dict[str, Any]] = []

    for i, ex in enumerate(_CORE_EXEMPLARS, start=1):
        decision = ex["decision_type"]
        items.append({
            "id": f"QT_{i:04d}",
            **ex,
            "primary_investment_question": understand_question(ex["literal_question"])["primary_investment_question"],
            "correct_response_structure": RESPONSE_STRUCTURE_BY_DECISION.get(decision, ""),
            "editorial_notes": "Spec acceptance exemplar.",
            "source": "spec_exemplar",
        })

    # IIC-backed entries
    iic_items = _from_iic()
    seen_literals = {x["literal_question"] for x in items}
    for entry in iic_items:
        if entry["literal_question"] not in seen_literals:
            items.append(entry)
            seen_literals.add(entry["literal_question"])
        if len(items) >= TARGET_TAXONOMY_COUNT:
            return tuple(items[:TARGET_TAXONOMY_COUNT])

    # Phrasing variants across companies
    idx = len(items) + 1
    for template, decision in _PHRASING_VARIANTS:
        for ticker, company in _COMPANIES:
            if len(items) >= TARGET_TAXONOMY_COUNT:
                break
            literal = template.format(company=company)
            if literal in seen_literals:
                continue
            seen_literals.add(literal)
            understood = understand_question(literal, ticker=ticker, company=company)
            items.append({
                "id": f"QT_{idx:04d}",
                "literal_question": literal,
                "investor_meaning": understood["investor_meaning"],
                "decision_type": decision,
                "research_objective": RESEARCH_OBJECTIVES.get(decision, understood["research_objective"]),
                "primary_investment_question": understood["primary_investment_question"],
                "expected_deliverable": understood["expected_deliverable"],
                "correct_response_structure": RESPONSE_STRUCTURE_BY_DECISION.get(decision, ""),
                "editorial_notes": "",
                "ticker": ticker,
                "source": "phrasing_variant",
            })
            idx += 1
        if len(items) >= TARGET_TAXONOMY_COUNT:
            break

    return tuple(items[:TARGET_TAXONOMY_COUNT])


QUESTION_TAXONOMY: tuple[dict[str, Any], ...] = _build_taxonomy()


def list_taxonomy(*, decision_type: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    items = list(QUESTION_TAXONOMY)
    if decision_type:
        items = [q for q in items if q.get("decision_type") == decision_type]
    return items[:limit]


def get_taxonomy_entry(entry_id: str) -> dict[str, Any] | None:
    for q in QUESTION_TAXONOMY:
        if q.get("id") == entry_id:
            return dict(q)
    return None
