"""Project Atlas — Institutional Intelligence Case Study V1.0 (HELD OUT).

CRITICAL RULES
--------------
1. NEVER import this module into matchers, composers, gold patterns, adversarial,
   family_classifier, or ic_case_study detectors.
2. NEVER train on these questions.
3. Use only for evaluation / scorecards.
4. A high score means integrated IC reasoning on this set — not unbounded proof
   of "genuine intelligence."

This bank deliberately mixes accounting, valuation, macro, corporate finance,
behavioural finance and evidence quality. There is no single correct investment
conclusion — only better or worse reasoning.
"""

from __future__ import annotations

from typing import Any

NEVER_TRAIN = True
EVALUATION_ONLY = True
CASE_ID = "project_atlas_ic_v1"
CASE_TITLE = "Project Atlas — AGIB Institutional Intelligence Case Study V1.0"
TOTAL_RUBRIC_POINTS = 200

# Shared dossier prepended by the scorecard (engine never sees category labels).
CASE_FACTS = """
PROJECT ATLAS — IC RESEARCH DOSSIER (fictional company for reasoning test).
Atlas Engineering Ltd.: industrial automation 45%, defence electronics 30%, AI factory software 15%, after-sales 10%.
Geography: India 58%, Europe 22%, USA 15%, Other 5%.
Five-year history (₹ cr): FY22–FY26 Revenue 8000,9200,10800,13200,15900; EBITDA margin 18%,19%,20%,18%,16%;
Net profit 620,760,920,1080,1210; FCF 710,690,420,120,-260; ROE 22%,23%,24%,19%,15%; ROIC 19%,21%,22%,18%,14%;
Debt 2000,2400,3000,4500,6800.
Market: price ₹920 (52w high 1380 / low 780); mcap ₹54000 cr; EV ₹60800 cr; P/E 44× (hist avg 24×);
EV/EBITDA 26× (peers 18×); PEG 3.1.
Management: CEO “demand never stronger”; CFO “WC pressures temporary”; IR “AI business will double in two years”.
Latest quarter: Revenue +28%; Net profit +18%; operating margin 17%↓; FCF -₹140 cr; receivables +52%;
inventory +37%; debt +41%; interest expense +49%.
Macro: RBI cut 50 bps; oil +38%; USD/INR 82→88; inflation 6.9%; PMI 56; ₹90,000 cr manufacturing incentive.
News: Reuters — Atlas wins ₹8,500 cr defence contract; NSE — no filing yet; Twitter — CEO resigning; Company — no confirmation.
Analysts: Broker A BUY tgt 1500; B SELL tgt 760; C HOLD tgt 980; consensus “positive”.
Other: largest customer 31%; patent expiry next year; ESG improving; auditor changed; promoter pledge 12%.
Valuation: DCF intrinsic ₹970; reverse DCF implies 18% annual FCF growth for 10 years; residual income ₹880; comps ₹810.
Hidden contradictions: revenue↑ margins↓; profit↑ cash↓; debt↑ ROE↓ ROIC↓; management optimistic vs WC/interest↑;
share price↓ vs consensus positive; Reuters vs no NSE filing.
RULES: No Buy/Sell/Hold recommendation; no price target as advice; separate evidence quality; show uncertainty.
""".strip()

# Rubric area weights (sum 200)
RUBRIC_AREAS: dict[str, int] = {
    "evidence_collection": 20,
    "evidence_weighting": 20,
    "accounting_reasoning": 20,
    "valuation_reasoning": 20,
    "corporate_finance": 15,
    "macro_reasoning": 15,
    "contradiction_handling": 20,
    "alternative_hypotheses": 15,
    "devils_advocate": 15,
    "evidence_boundaries": 15,
    "plain_english": 10,
    "appropriate_uncertainty": 15,
}

BAN_COMMON = ["buy now", "sell now", "definitely buy", "definitely sell", "target price advice"]

QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "A01",
        "section": "A",
        "areas": ["contradiction_handling", "plain_english", "appropriate_uncertainty"],
        "marks": 12,
        "mode_hint": "ic_executive_assessment",
        "question": "Give an executive assessment. Maximum 200 words.",
        "must_include": ["cash", "roic", "contradict"],
        "must_not_include": ["buy", "sell", "hold"],
        "max_words": 220,
    },
    {
        "id": "A02",
        "section": "A",
        "areas": ["evidence_collection", "plain_english"],
        "marks": 6,
        "mode_hint": "ic_strengths",
        "question": "List five biggest strengths.",
        "must_include": ["defence", "growth", "automation"],
        "must_not_include": ["definitely buy"],
        "min_items": 5,
    },
    {
        "id": "A03",
        "section": "A",
        "areas": ["evidence_collection", "contradiction_handling"],
        "marks": 6,
        "mode_hint": "ic_risks",
        "question": "List five biggest risks.",
        "must_include": ["cash", "debt", "receivable"],
        "must_not_include": ["definitely sell"],
        "min_items": 5,
    },
    {
        "id": "B04",
        "section": "B",
        "areas": ["accounting_reasoning", "alternative_hypotheses"],
        "marks": 12,
        "mode_hint": "ic_fcf_explanations",
        "question": (
            "Why is Free Cash Flow negative despite higher revenue? "
            "Give at least six possible explanations. Rank them."
        ),
        "must_include": ["working capital", "receivable", "inventory", "capex"],
        "must_not_include": ["buy", "sell"],
        "min_explanations": 6,
    },
    {
        "id": "B05",
        "section": "B",
        "areas": ["accounting_reasoning", "contradiction_handling"],
        "marks": 8,
        "mode_hint": "ic_profit_quality",
        "question": "Is profit quality improving or deteriorating? Explain.",
        "must_include": ["deteriorat", "cash", "receivable"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "B06",
        "section": "B",
        "areas": ["accounting_reasoning", "evidence_collection"],
        "marks": 8,
        "mode_hint": "ic_management_questions",
        "question": "What questions would you ask management? Minimum 15.",
        "must_include": ["working capital", "receivable", "auditor", "defence"],
        "must_not_include": ["buy", "sell"],
        "min_questions": 15,
    },
    {
        "id": "C07",
        "section": "C",
        "areas": ["valuation_reasoning"],
        "marks": 8,
        "mode_hint": "ic_valuation_divergence",
        "question": "Why do DCF, Comparable and Residual Income give different values?",
        "must_include": ["dcf", "residual", "comparable"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "C08",
        "section": "C",
        "areas": ["valuation_reasoning", "appropriate_uncertainty"],
        "marks": 6,
        "mode_hint": "ic_valuation_weight",
        "question": "Which valuation deserves most weight? Why?",
        "must_include": ["cash", "reverse", "triang"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "C09",
        "section": "C",
        "areas": ["valuation_reasoning", "evidence_boundaries"],
        "marks": 6,
        "mode_hint": "ic_dcf_unreliable",
        "question": "List assumptions that make DCF unreliable.",
        "must_include": ["terminal", "wacc", "working capital"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D10",
        "section": "D",
        "areas": ["corporate_finance"],
        "marks": 8,
        "mode_hint": "ic_roic_value",
        "question": "Has management created shareholder value? Use ROIC vs Cost of Capital.",
        "must_include": ["roic", "cost of capital", "wacc"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "D11",
        "section": "D",
        "areas": ["corporate_finance", "appropriate_uncertainty"],
        "marks": 7,
        "mode_hint": "ic_financing_tradeoffs",
        "question": (
            "Would you issue equity, raise debt, or slow expansion? Explain. "
            "Do not recommend a financing action unless supported by evidence; discuss trade-offs."
        ),
        "must_include": ["trade-off", "debt", "equity", "expansion"],
        "must_not_include": ["definitely issue", "definitely raise"],
    },
    {
        "id": "E12",
        "section": "E",
        "areas": ["macro_reasoning"],
        "marks": 8,
        "mode_hint": "ic_macro_transmission",
        "question": "Explain how Oil, Rates, FX and PMI affect Atlas.",
        "must_include": ["oil", "rate", "fx", "pmi"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "E13",
        "section": "E",
        "areas": ["macro_reasoning", "evidence_weighting"],
        "marks": 7,
        "mode_hint": "ic_macro_rank",
        "question": "Rank macro risks.",
        "must_include": ["oil", "rank"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "F14",
        "section": "F",
        "areas": ["evidence_weighting", "evidence_boundaries"],
        "marks": 7,
        "mode_hint": "ic_reuters_update",
        "question": "Should Reuters change your assessment?",
        "must_include": ["filing", "nse", "not"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "F15",
        "section": "F",
        "areas": ["evidence_weighting", "evidence_boundaries"],
        "marks": 6,
        "mode_hint": "ic_twitter_update",
        "question": "Should Twitter change your assessment?",
        "must_include": ["ignor", "confirm", "social"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "F16",
        "section": "F",
        "areas": ["evidence_weighting", "behavioural"],
        "marks": 6,
        "mode_hint": "ic_analyst_conflict",
        "question": "How should conflicting analyst reports be handled?",
        "must_include": ["assumption", "consensus", "evidence"],
        "must_not_include": ["average the targets"],
    },
    {
        "id": "G17",
        "section": "G",
        "areas": ["devils_advocate", "alternative_hypotheses"],
        "marks": 5,
        "mode_hint": "ic_bull_case",
        "question": "Argue the Bull Case.",
        "must_include": ["growth", "temporary", "defence"],
        "must_not_include": ["buy"],
    },
    {
        "id": "G18",
        "section": "G",
        "areas": ["devils_advocate", "alternative_hypotheses"],
        "marks": 5,
        "mode_hint": "ic_bear_case",
        "question": "Argue the Bear Case.",
        "must_include": ["cash", "leverage", "multiple"],
        "must_not_include": ["sell"],
    },
    {
        "id": "G19",
        "section": "G",
        "areas": ["devils_advocate", "appropriate_uncertainty"],
        "marks": 5,
        "mode_hint": "ic_both_wrong",
        "question": "Argue why both could be wrong.",
        "must_include": ["both", "wrong", "muddle"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G20",
        "section": "G",
        "areas": ["devils_advocate", "alternative_hypotheses"],
        "marks": 5,
        "mode_hint": "ic_scenarios",
        "question": "Give three future scenarios: Bull, Base, Bear.",
        "must_include": ["bull", "base", "bear"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "H21",
        "section": "H",
        "areas": ["evidence_collection", "self_critique"],
        "marks": 5,
        "mode_hint": "ic_list_assumptions",
        "question": "List every assumption.",
        "must_include": ["assumption", "working capital", "valuation"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "H22",
        "section": "H",
        "areas": ["evidence_collection", "evidence_weighting"],
        "marks": 5,
        "mode_hint": "ic_support_assumptions",
        "question": "List evidence supporting each assumption.",
        "must_include": ["support", "evidence", "financial"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "H23",
        "section": "H",
        "areas": ["contradiction_handling", "evidence_weighting"],
        "marks": 5,
        "mode_hint": "ic_contradict_assumptions",
        "question": "List evidence contradicting each assumption.",
        "must_include": ["contradict", "cash", "filing"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "H24",
        "section": "H",
        "areas": ["evidence_boundaries", "appropriate_uncertainty"],
        "marks": 5,
        "mode_hint": "ic_falsifiers",
        "question": "What evidence would change your conclusion?",
        "must_include": ["fcf", "filing", "change"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "H25",
        "section": "H",
        "areas": ["evidence_boundaries", "evidence_collection"],
        "marks": 5,
        "mode_hint": "ic_missing_evidence",
        "question": "What evidence is still missing?",
        "must_include": ["missing", "cash-flow", "filing"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "I26",
        "section": "I",
        "areas": ["behavioural", "evidence_weighting"],
        "marks": 10,
        "mode_hint": "ic_behavioural",
        "question": (
            "Identify Anchoring, Confirmation Bias, Recency Bias, Narrative Fallacy, "
            "and Survivorship Bias that analysts may fall into."
        ),
        "must_include": [
            "anchoring",
            "confirmation",
            "recency",
            "narrative",
            "survivorship",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "J27",
        "section": "J",
        "areas": ["evidence_weighting"],
        "marks": 6,
        "mode_hint": "ic_evidence_rank",
        "question": "Which evidence is highest quality? Rank all evidence.",
        "must_include": ["filing", "financial", "twitter", "rank"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "J28",
        "section": "J",
        "areas": ["evidence_boundaries"],
        "marks": 5,
        "mode_hint": "ic_ignore_evidence",
        "question": "Which evidence should be ignored? Why?",
        "must_include": ["twitter", "target", "ignor"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "J29",
        "section": "J",
        "areas": ["evidence_boundaries", "appropriate_uncertainty"],
        "marks": 5,
        "mode_hint": "ic_cannot_conclude",
        "question": "What cannot be concluded?",
        "must_include": ["cannot", "buy", "fraud"],
        "must_not_include": ["definitely buy"],
        # "buy" appears in "cannot conclude Buy/Sell" — allow via must_include buy as word in context;
        # ban only definite recommendations handled in scorecard specially.
    },
    {
        "id": "J30",
        "section": "J",
        "areas": ["appropriate_uncertainty", "evidence_boundaries"],
        "marks": 8,
        "mode_hint": "ic_confidence_scores",
        "question": (
            "Provide a confidence score (0–100%) for each major conclusion and explain "
            "what additional evidence would increase or decrease that confidence."
        ),
        "must_include": ["%", "confidence", "evidence"],
        "must_not_include": ["100% certain"],
    },
]

assert sum(int(q["marks"]) for q in QUESTIONS) == TOTAL_RUBRIC_POINTS
assert NEVER_TRAIN is True
