"""TCS lifecycle curriculum — superseded by institutional_investor_curriculum v1.0.

Retained for reference. Primary benchmarks: institutional_investor_curriculum.
"""

from __future__ import annotations

from typing import Any

from institutional_writing_benchmark.schema import LIFECYCLE_PLAYBOOKS, PLAYBOOK_TITLES

_TICKER = "TCS"
_COMPANY = "Tata Consultancy Services"

# (playbook, question) pairs in lifecycle order — exactly 100 questions
_TCS_QUESTIONS: tuple[tuple[str, str], ...] = (
    # Playbook 1 — Investment Assessment (1–5)
    ("investment_assessment", "Should I invest in TCS today?"),
    ("investment_assessment", "Is TCS a high-quality business?"),
    ("investment_assessment", "What is the investment thesis for TCS?"),
    ("investment_assessment", "What are the biggest reasons to own TCS?"),
    ("investment_assessment", "What would stop you from researching TCS further?"),
    # Playbook 2 — Business Quality (6–10)
    ("business_quality", "Does TCS have a durable competitive advantage?"),
    ("business_quality", "Why do customers continue choosing TCS?"),
    ("business_quality", "Does TCS have pricing power?"),
    ("business_quality", "Is TCS becoming stronger or weaker as a business?"),
    ("business_quality", "What makes TCS difficult to compete against?"),
    # Playbook 3 — Management Quality (11–15)
    ("management_quality", "Is TCS management allocating capital effectively?"),
    ("management_quality", "Has management historically delivered on guidance?"),
    ("management_quality", "How shareholder-friendly is TCS management?"),
    ("management_quality", "What decisions by management created the most value?"),
    ("management_quality", "What concerns exist regarding management execution?"),
    # Playbook 4 — Financial Quality (16–20)
    ("financial_quality", "Are TCS financials improving?"),
    ("financial_quality", "How strong is cash generation?"),
    ("financial_quality", "Is the balance sheet a competitive advantage?"),
    ("financial_quality", "Are margins sustainable?"),
    ("financial_quality", "What are the most important financial strengths and weaknesses?"),
    # Playbook 5 — Valuation (21–25)
    ("valuation", "Is TCS trading above or below its historical valuation?"),
    ("valuation", "What assumptions are priced into today's valuation?"),
    ("valuation", "Is valuation supported by fundamentals?"),
    ("valuation", "What could justify multiple expansion?"),
    ("valuation", "What could lead to multiple contraction?"),
    # Playbook 6 — Growth (26–30)
    ("growth", "What will drive TCS growth over the next five years?"),
    ("growth", "Which business segments matter most?"),
    ("growth", "How important is AI for future growth?"),
    ("growth", "Where could growth disappoint?"),
    ("growth", "What growth assumptions appear most optimistic?"),
    # Playbook 7 — Risks (31–35)
    ("risks", "What are the three biggest risks?"),
    ("risks", "Which risk is currently underestimated?"),
    ("risks", "What could permanently damage the investment thesis?"),
    ("risks", "Which macro risks matter most?"),
    ("risks", "Which company-specific risks deserve monitoring?"),
    # Playbook 8 — Investment Debate (36–40)
    ("investment_debate", "What is the current investment debate around TCS?"),
    ("investment_debate", "Why do bulls like TCS?"),
    ("investment_debate", "Why are bears cautious?"),
    ("investment_debate", "Which side currently has stronger evidence?"),
    ("investment_debate", "What evidence would change the debate?"),
    # Playbook 9 — Earnings (41–45)
    ("earnings", "What changed after the latest earnings?"),
    ("earnings", "What remained unchanged?"),
    ("earnings", "Did earnings strengthen or weaken the thesis?"),
    ("earnings", "What surprised the market?"),
    ("earnings", "What should investors monitor next quarter?"),
    # Playbook 10 — Competitive Position (46–50)
    ("competitive_position", "Compare TCS with Infosys."),
    ("competitive_position", "Compare TCS with Accenture."),
    ("competitive_position", "Is TCS gaining or losing market share?"),
    ("competitive_position", "Which competitor represents the biggest threat?"),
    ("competitive_position", "What differentiates TCS from peers?"),
    # Playbook 11 — Industry (51–55)
    ("industry", "Where is the Indian IT industry today?"),
    ("industry", "Is the sector attractive?"),
    ("industry", "Which structural trends matter most?"),
    ("industry", "How does TCS benefit from industry trends?"),
    ("industry", "Which industry changes could hurt TCS?"),
    # Playbook 12 — Portfolio Fit (56–60)
    ("portfolio_fit", "What role could TCS play in a diversified portfolio?"),
    ("portfolio_fit", "What type of investor would find TCS suitable?"),
    ("portfolio_fit", "Which existing holdings overlap with TCS?"),
    ("portfolio_fit", "What alternatives should investors compare?"),
    ("portfolio_fit", "Under what circumstances would TCS deserve a larger allocation?"),
    # Playbook 13 — Macro Impact (61–65)
    ("macro_impact", "How do interest rates affect TCS?"),
    ("macro_impact", "How does USD/INR influence earnings?"),
    ("macro_impact", "Which macro variables matter most?"),
    ("macro_impact", "What recession scenario should investors consider?"),
    ("macro_impact", "Which global events could materially affect TCS?"),
    # Playbook 14 — Monitoring (66–70)
    ("monitoring", "Which KPIs should investors monitor?"),
    ("monitoring", "Which events would strengthen the thesis?"),
    ("monitoring", "Which events would weaken the thesis?"),
    ("monitoring", "What would make you revisit the investment?"),
    ("monitoring", "What early warning signals matter most?"),
    # Playbook 15 — Historical Perspective (71–75)
    ("historical_perspective", "How has TCS evolved over the last decade?"),
    ("historical_perspective", "What has consistently driven shareholder returns?"),
    ("historical_perspective", "Which historical decisions mattered most?"),
    ("historical_perspective", "What lessons does TCS's history provide?"),
    ("historical_perspective", "Has the competitive position improved or deteriorated?"),
    # Playbook 16 — Scenario Analysis (76–80)
    ("scenario_analysis", "What is the base case?"),
    ("scenario_analysis", "What is the upside scenario?"),
    ("scenario_analysis", "What is the downside scenario?"),
    ("scenario_analysis", "Which assumptions matter most?"),
    ("scenario_analysis", "Which scenario appears most plausible?"),
    # Playbook 17 — Decision Support (81–85)
    ("decision_support", "What do I still need to know before investing?"),
    ("decision_support", "Which research questions remain unanswered?"),
    ("decision_support", "Which evidence is strongest today?"),
    ("decision_support", "Which evidence is weakest?"),
    ("decision_support", "What is the biggest unknown?"),
    # Playbook 18 — Explainability (86–90)
    ("explainability", "Why does AGI believe TCS has pricing power?"),
    ("explainability", "Show the evidence supporting your thesis."),
    ("explainability", "Which evidence contradicts the thesis?"),
    ("explainability", "How confident are you in this assessment?"),
    ("explainability", "What would reduce your confidence?"),
    # Playbook 19 — Communication (91–95)
    ("communication", "Explain TCS as if I were a new investor."),
    ("communication", "Explain TCS in plain English."),
    ("communication", "Summarize TCS in five bullet points."),
    ("communication", "Give me a one-minute investment briefing."),
    ("communication", "What are the three things every investor should know?"),
    # Playbook 20 — Institutional Thinking (96–100)
    ("institutional_thinking", "If you were presenting TCS to an investment committee, what would you say?"),
    ("institutional_thinking", "What is the single most important investment question today?"),
    ("institutional_thinking", "If you had only five minutes to research TCS, where would you focus?"),
    ("institutional_thinking", "What would make you change your current view?"),
    ("institutional_thinking", "What should an institutional investor understand before making any decision on TCS?"),
)

_EDITORIAL_NOTES: dict[str, str] = {
    "investment_assessment": "Frame as understanding, not recommendation. Lead with why this matters.",
    "business_quality": "Explain mechanism of advantage — do not label quality without reasoning.",
    "management_quality": "Connect capital allocation to shareholder outcomes with evidence.",
    "financial_quality": "Explain implications of financial trends, not just report numbers.",
    "valuation": "Separate expectations from fundamentals; never say cheap or expensive without context.",
    "growth": "Identify drivers, segments, and where optimism may be overstated.",
    "risks": "Prioritize three risks; distinguish underestimated vs headline risks.",
    "investment_debate": "Present both sides fairly; identify what would shift the debate.",
    "earnings": "Separate what changed from what did not; link to thesis.",
    "competitive_position": "Business comparison before financial metrics.",
    "industry": "Sector context before company implications.",
    "portfolio_fit": "Role in portfolio without allocation advice.",
    "macro_impact": "Link macro variables to earnings and valuation sensitivities.",
    "monitoring": "Actionable KPIs and thesis-strengthening vs weakening events.",
    "historical_perspective": "Decade arc with lessons for forward assessment.",
    "scenario_analysis": "Base, upside, downside with key assumptions explicit.",
    "decision_support": "Surface gaps in knowledge — what remains unknown.",
    "explainability": "Show evidence chain; state confidence and what would reduce it.",
    "communication": "Plain English without dumbing down institutional rigor.",
    "institutional_thinking": "Investment committee voice — prioritization over comprehensiveness.",
}

EXPECTED_STRUCTURES: dict[str, str] = {
    "investment_assessment": "executive_summary → investment_debate → evidence → uncertainties → conclusion → questions",
    "business_quality": "executive_summary → what_matters_most → investment_debate → evidence → uncertainties → conclusion",
    "management_quality": "executive_summary → management_quality → capital_allocation → evidence → uncertainties → conclusion",
    "financial_quality": "executive_summary → financial_strengths_weaknesses → evidence → uncertainties → conclusion",
    "valuation": "executive_summary → current_expectations → historical_context → evidence → risks → conclusion",
    "growth": "executive_summary → growth_drivers → segments → evidence → risks → conclusion",
    "risks": "executive_summary → primary_risks → evidence → probability → monitoring → conclusion",
    "investment_debate": "executive_summary → bull_case → bear_case → evidence_balance → what_changes_debate",
    "earnings": "executive_summary → what_changed → what_didnt_change → market_implications → evidence → monitoring",
    "competitive_position": "executive_summary → business_comparison → financial_comparison → competitive_position → evidence → conclusion",
    "industry": "executive_summary → sector_context → structural_trends → company_implications → conclusion",
    "portfolio_fit": "executive_summary → role_in_portfolio → overlap → alternatives → conclusion",
    "macro_impact": "executive_summary → macro_drivers → company_implications → evidence → conclusion",
    "monitoring": "executive_summary → monitoring_indicators → thesis_triggers → evidence → conclusion",
    "historical_perspective": "executive_summary → decade_evolution → return_drivers → lessons → conclusion",
    "scenario_analysis": "executive_summary → base_case → upside → downside → key_assumptions → conclusion",
    "decision_support": "executive_summary → knowledge_gaps → strongest_evidence → weakest_evidence → conclusion",
    "explainability": "executive_summary → thesis → supporting_evidence → contradicting_evidence → confidence",
    "communication": "executive_summary → plain_english → key_points → briefing → conclusion",
    "institutional_thinking": "executive_summary → investment_debate → priority_question → focus_areas → committee_brief",
}


def _build_tcs_curriculum() -> tuple[dict[str, Any], ...]:
    assert len(_TCS_QUESTIONS) == 100
    items: list[dict[str, Any]] = []
    playbook_index: dict[str, int] = {}

    for idx, (playbook, question) in enumerate(_TCS_QUESTIONS, start=1):
        playbook_num = LIFECYCLE_PLAYBOOKS.index(playbook) + 1
        q_in_playbook = playbook_index.get(playbook, 0) + 1
        playbook_index[playbook] = q_in_playbook

        items.append({
            "id": f"IWB_{idx:03d}",
            "question": question,
            "playbook": playbook,
            "playbook_title": PLAYBOOK_TITLES[playbook],
            "playbook_number": playbook_num,
            "question_in_playbook": q_in_playbook,
            "category": playbook,
            "ticker": _TICKER,
            "company": _COMPANY,
            "phase": 1,
            "curriculum": "tcs_lifecycle_v1",
            "expected_structure": EXPECTED_STRUCTURES.get(playbook, "narrative_default"),
            "editorial_notes": _EDITORIAL_NOTES.get(playbook, ""),
            "latest_score": None,
            "revision_history": [],
        })
    return tuple(items)


TCS_CURRICULUM: tuple[dict[str, Any], ...] = _build_tcs_curriculum()
