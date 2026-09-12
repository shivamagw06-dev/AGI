"""Append-only institutional memory corpus — seeded learning history (never overwrite)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Immutable seeded institutional memory. New learning updates APPEND only via learning_update.
CORPUS: dict[str, dict[str, Any]] = {
    "HDFCBANK": {
        "ticker": "HDFCBANK",
        "name": "HDFC Bank",
        "theses": [
            {
                "version": 1,
                "date": "2023-03-15",
                "stance": "bullish",
                "author": "business_analyst",
                "evidence": ["Franchise deposit strength", "Retail loan growth"],
                "confidence": 0.72,
                "outcome": "partially_correct",
                "outcome_note": "Franchise held; NIM path more volatile than assumed",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-06-20",
                "stance": "neutral",
                "author": "committee",
                "evidence": ["Deposit cost pressure", "Merger integration lag"],
                "confidence": 0.58,
                "outcome": "correct",
                "outcome_note": "Neutral stance matched consolidation period",
                "overwritten": False,
            },
            {
                "version": 3,
                "date": "2025-11-10",
                "stance": "bullish",
                "author": "cio",
                "evidence": ["Liability franchise repair", "Credit cost contained", "FIL guidance consistency"],
                "confidence": 0.68,
                "outcome": "open",
                "outcome_note": "Live thesis — awaiting outcome review",
                "overwritten": False,
            },
        ],
        "analyst_opinions": [
            {
                "version": 1,
                "date": "2023-03-15",
                "role": "business",
                "opinion": "Quality compounder with durable liability franchise",
                "reasoning": "CASA + distribution moat",
                "evidence": ["Branch density", "Retail mix"],
                "confidence": 0.74,
                "uncertainty": ["Deposit repricing lag"],
                "accuracy": 0.66,
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-06-20",
                "role": "financial",
                "opinion": "NIM compression risk elevated near term",
                "reasoning": "Funding cost cycle",
                "evidence": ["Deposit rate prints", "Loan mix shift"],
                "confidence": 0.7,
                "uncertainty": ["Policy cut timing"],
                "accuracy": 0.78,
                "overwritten": False,
            },
            {
                "version": 3,
                "date": "2025-11-10",
                "role": "risk",
                "opinion": "Unsecured / cyclical credit watch but core book sound",
                "reasoning": "Credit cost still contained vs peers",
                "evidence": ["GNPA trend", "PCR"],
                "confidence": 0.64,
                "uncertainty": ["Regulatory risk weights"],
                "accuracy": None,
                "overwritten": False,
            },
        ],
        "committee_decisions": [
            {
                "version": 1,
                "date": "2023-03-18",
                "consensus": "bullish",
                "minority": "neutral — integration risk",
                "vote": {"bullish": 5, "neutral": 2, "bearish": 0},
                "challenges": ["Merger execution", "Deposit costs"],
                "evidence": ["FIL AR excerpts", "Peer NIM comparison"],
                "open_questions": ["How fast will liability franchise normalise?"],
                "decision": "Maintain high-quality bank exposure suitability",
                "review_date": "2024-03-18",
                "outcome_quality": 0.7,
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-06-22",
                "consensus": "neutral",
                "minority": "bullish — franchise durability",
                "vote": {"bullish": 2, "neutral": 4, "bearish": 1},
                "challenges": ["Growth lag vs private peers"],
                "evidence": ["FDI material change notes", "MII trust score"],
                "open_questions": ["When does loan growth re-accelerate?"],
                "decision": "Watchlist / suitability review — no order language",
                "review_date": "2025-06-22",
                "outcome_quality": 0.8,
                "minority_was_correct": False,
                "overwritten": False,
            },
            {
                "version": 3,
                "date": "2025-11-12",
                "consensus": "cautiously_bullish",
                "minority": "neutral — rate path uncertain",
                "vote": {"bullish": 4, "neutral": 3, "bearish": 0},
                "challenges": ["Scenario probability calibration"],
                "evidence": ["FIE base case", "CIG rate transmission", "IKG bank dependencies"],
                "open_questions": ["Credit cost under soft landing?"],
                "decision": "Thesis upgrade to bullish with explicit triggers",
                "review_date": "2026-05-12",
                "outcome_quality": None,
                "overwritten": False,
            },
        ],
        "forecasts": [
            {
                "version": 1,
                "date": "2023-03-15",
                "distribution": {"bull": 0.30, "base": 0.40, "bear": 0.18, "stress": 0.06, "recovery": 0.06},
                "most_likely": "base",
                "actual_outcome": "bear",
                "calibration": 0.55,
                "learning": "Underweighted deposit-cost bear path",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-06-20",
                "distribution": {"bull": 0.18, "base": 0.42, "bear": 0.24, "stress": 0.08, "recovery": 0.08},
                "most_likely": "base",
                "actual_outcome": "base",
                "calibration": 0.82,
                "learning": "Better calibrated after funding-cost lesson",
                "overwritten": False,
            },
            {
                "version": 3,
                "date": "2025-11-10",
                "distribution": {"bull": 0.24, "base": 0.40, "bear": 0.20, "stress": 0.08, "recovery": 0.08},
                "most_likely": "base",
                "actual_outcome": None,
                "calibration": None,
                "learning": None,
                "overwritten": False,
            },
        ],
        "management": [
            {
                "version": 1,
                "date": "2023-03-15",
                "guidance_credibility": 0.7,
                "capital_allocation": "conservative",
                "execution": "solid",
                "leadership_change": False,
                "notes": "Guidance reliability moderate; integration messaging dense",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2025-11-10",
                "guidance_credibility": 0.74,
                "capital_allocation": "disciplined",
                "execution": "improving",
                "leadership_change": False,
                "notes": "MII soft trust improved on delivery vs prior prints",
                "overwritten": False,
            },
        ],
        "decisions": [
            {
                "version": 1,
                "date": "2023-03-18",
                "question": "Does HDFC Bank improve a quality India book?",
                "evidence": ["FIL", "PIL peers", "PIO suitability"],
                "reasoning": "Franchise quality outweighs near-term NIM noise",
                "alternatives": ["Wait for deposit normalisation", "Prefer SBI value"],
                "decision": "Suitability constructive — not a buy order",
                "confidence": 0.7,
                "outcome": "mixed",
                "lessons": ["Weight funding-cost timing more explicitly"],
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-06-22",
                "question": "Should stance shift after funding-cost surprise?",
                "evidence": ["Forecast miss v1", "Committee minority notes"],
                "reasoning": "Probability mass needed rebalancing toward bear/base",
                "alternatives": ["Remain bullish", "Move to bearish"],
                "decision": "Neutral with review triggers",
                "confidence": 0.66,
                "outcome": "correct",
                "lessons": ["Update FIE priors after liability shocks"],
                "overwritten": False,
            },
        ],
        "confidence_history": [
            {"date": "2023-03-15", "confidence": 0.72, "reason": "Initial franchise thesis", "evidence_improvements": [], "missing_evidence": ["Post-merger liability data"]},
            {"date": "2024-06-20", "confidence": 0.58, "reason": "Funding-cost miss reduced confidence", "evidence_improvements": ["Deposit rate series"], "missing_evidence": ["Stabilisation confirmation"]},
            {"date": "2025-11-10", "confidence": 0.68, "reason": "Evidence coverage improved via FIL/MII/FIE", "evidence_improvements": ["FIL corpus", "FIE triggers"], "missing_evidence": ["Next credit-cost print"]},
        ],
        "evidence_history": [
            {"date": "2023-03-15", "items": ["Annual report excerpts", "Peer NIM"], "retained": True},
            {"date": "2024-06-20", "items": ["FDI deposit-cost delta", "MII credibility"], "retained": True},
            {"date": "2025-11-10", "items": ["FIE scenario pack", "IKG rate dependencies", "CIG transmission"], "retained": True},
        ],
        "mistakes": [
            {
                "id": "m_hdfc_2023_prob",
                "date": "2023-09-30",
                "context": "Forecast v1 missed — actual path closer to bear on NIM",
                "error_type": "probability_error",
                "example": "Bull/base mass too high vs deposit-cost bear path",
                "expected": "base",
                "observed": "bear",
                "lesson": "Increase bear prior when liability costs are rising faster than street",
            },
            {
                "id": "m_hdfc_2023_timing",
                "date": "2024-01-15",
                "context": "Bullish franchise thesis eventually directionally right but early",
                "error_type": "timing_error",
                "example": "Thesis correct but too early into merger integration",
                "expected": "re-rating within 2Q",
                "observed": "lagged into 2025",
                "lesson": "Attach explicit time triggers to bull cases",
            },
            {
                "id": "m_hdfc_2023_mgmt",
                "date": "2023-12-01",
                "context": "Guidance on integration timeline relied on too heavily",
                "error_type": "management_error",
                "example": "Guidance relied on too heavily",
                "expected": "guidance delivery on stated lag",
                "observed": "longer liability normalisation",
                "lesson": "Haircut management timeline confidence until FIL confirms",
            },
        ],
        "lessons": [
            {
                "date": "2024-06-22",
                "expected": "Base path with stable NIM",
                "observed": "Funding-cost pressure / slower growth",
                "difference": "Liability side weaker than assumed",
                "reason": "Probability and timing errors on deposit costs",
                "lesson": "Fund institutional memory into FIE priors and committee challenges",
                "updated_knowledge": "Bank theses must carry explicit deposit-cost triggers",
            },
            {
                "date": "2025-11-12",
                "expected": "Neutral consolidation continues",
                "observed": "Liability repair signals emerging",
                "difference": "Evidence improved enough to upgrade cautiously",
                "reason": "FIL/MII/FIE coverage reduced uncertainty",
                "lesson": "Confidence can rise only with evidenced trigger progress",
                "updated_knowledge": "Upgrade path requires measurable CASA/NIM triggers",
            },
        ],
        "company_timeline": [
            {"date": "2023-03", "domain": "business", "note": "Quality franchise thesis opened"},
            {"date": "2023-09", "domain": "financial", "note": "NIM / deposit-cost stress observed"},
            {"date": "2024-06", "domain": "committee", "note": "Stance moved to neutral"},
            {"date": "2025-11", "domain": "valuation_risk", "note": "Cautious bullish with triggers"},
        ],
    },
    "TCS": {
        "ticker": "TCS",
        "name": "Tata Consultancy Services",
        "theses": [
            {
                "version": 1,
                "date": "2022-08-01",
                "stance": "bullish",
                "author": "sector_analyst",
                "evidence": ["Deal pipeline", "Margin discipline"],
                "confidence": 0.7,
                "outcome": "timing_miss",
                "outcome_note": "Demand slowdown arrived sooner",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-02-10",
                "stance": "neutral",
                "author": "committee",
                "evidence": ["CC growth soft", "Discretionary freeze"],
                "confidence": 0.62,
                "outcome": "correct",
                "outcome_note": "Neutral matched demand pause",
                "overwritten": False,
            },
            {
                "version": 3,
                "date": "2025-09-01",
                "stance": "cautiously_bullish",
                "author": "cio",
                "evidence": ["AI services adjacency", "USD translation", "FIE base recovery"],
                "confidence": 0.64,
                "outcome": "open",
                "overwritten": False,
            },
        ],
        "analyst_opinions": [
            {
                "version": 1,
                "date": "2022-08-01",
                "role": "sector",
                "opinion": "Best-in-class IT compounder",
                "reasoning": "Scale + execution",
                "evidence": ["Large deal wins"],
                "confidence": 0.75,
                "uncertainty": ["US budgets"],
                "accuracy": 0.55,
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-02-10",
                "role": "macro",
                "opinion": "US discretionary IT spend remains soft",
                "reasoning": "Enterprise budget caution",
                "evidence": ["Peer commentary", "USD"],
                "confidence": 0.7,
                "uncertainty": ["AI displacement vs enablement"],
                "accuracy": 0.8,
                "overwritten": False,
            },
        ],
        "committee_decisions": [
            {
                "version": 1,
                "date": "2024-02-12",
                "consensus": "neutral",
                "minority": "bullish AI upside",
                "vote": {"bullish": 2, "neutral": 5, "bearish": 0},
                "challenges": ["Growth timing"],
                "evidence": ["FIE scenarios", "IKG US enterprise customers"],
                "open_questions": ["When do large deals convert?"],
                "decision": "Neutral with AI catalyst monitor",
                "review_date": "2025-02-12",
                "outcome_quality": 0.78,
                "overwritten": False,
            }
        ],
        "forecasts": [
            {
                "version": 1,
                "date": "2022-08-01",
                "distribution": {"bull": 0.32, "base": 0.38, "bear": 0.18, "stress": 0.06, "recovery": 0.06},
                "most_likely": "bull",
                "actual_outcome": "bear",
                "calibration": 0.4,
                "learning": "Macro demand shock underweighted",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-02-10",
                "distribution": {"bull": 0.18, "base": 0.44, "bear": 0.22, "stress": 0.08, "recovery": 0.08},
                "most_likely": "base",
                "actual_outcome": "base",
                "calibration": 0.85,
                "learning": "Macro error corrected in priors",
                "overwritten": False,
            },
        ],
        "management": [
            {
                "version": 1,
                "date": "2024-02-10",
                "guidance_credibility": 0.8,
                "capital_allocation": "shareholder-friendly",
                "execution": "strong",
                "leadership_change": False,
                "notes": "Guidance conservative vs street",
                "overwritten": False,
            }
        ],
        "decisions": [
            {
                "version": 1,
                "date": "2024-02-12",
                "question": "Is TCS still a core IT quality holding?",
                "evidence": ["PIL peers", "FIE demand scenarios"],
                "reasoning": "Quality intact; growth timing uncertain",
                "alternatives": ["Rotate to INFY", "Increase AI barbell"],
                "decision": "Maintain quality suitability; monitor deal conversion",
                "confidence": 0.65,
                "outcome": "correct",
                "lessons": ["Separate franchise quality from demand-cycle timing"],
                "overwritten": False,
            }
        ],
        "confidence_history": [
            {"date": "2022-08-01", "confidence": 0.7, "reason": "Deal momentum", "evidence_improvements": [], "missing_evidence": ["US recession indicators"]},
            {"date": "2024-02-10", "confidence": 0.62, "reason": "Demand soft patch", "evidence_improvements": ["Peer prints"], "missing_evidence": ["Large-deal conversion"]},
            {"date": "2025-09-01", "confidence": 0.64, "reason": "AI adjacency + USD", "evidence_improvements": ["IKG tech graph"], "missing_evidence": ["Margin durability under AI mix"]},
        ],
        "evidence_history": [
            {"date": "2022-08-01", "items": ["Deal win releases"], "retained": True},
            {"date": "2024-02-10", "items": ["Sector demand notes", "Macro USD"], "retained": True},
        ],
        "mistakes": [
            {
                "id": "m_tcs_2022_macro",
                "date": "2023-01-20",
                "context": "Demand slowdown underweighted",
                "error_type": "macro_error",
                "example": "Unexpected US discretionary IT freeze",
                "expected": "bull",
                "observed": "bear",
                "lesson": "Bind IT bull cases to explicit US budget triggers",
            },
            {
                "id": "m_tcs_2022_reason",
                "date": "2023-03-01",
                "context": "Correct franchise data, wrong near-term inference",
                "error_type": "reasoning_error",
                "example": "Correct data, incorrect inference on growth persistence",
                "expected": "growth durability",
                "observed": "cyclical pause",
                "lesson": "Do not extrapolate deal wins without utilization confirmation",
            },
        ],
        "lessons": [
            {
                "date": "2024-02-12",
                "expected": "Bullish growth continuation",
                "observed": "Demand pause",
                "difference": "Macro cycle dominated franchise quality",
                "reason": "Macro + reasoning errors",
                "lesson": "Quality ≠ imminent outperformance",
                "updated_knowledge": "IT theses need demand-cycle gates",
            }
        ],
        "company_timeline": [
            {"date": "2022-08", "domain": "business", "note": "Bullish quality thesis"},
            {"date": "2023-01", "domain": "macro", "note": "Demand shock lesson"},
            {"date": "2024-02", "domain": "committee", "note": "Neutral stance"},
            {"date": "2025-09", "domain": "technology", "note": "Cautious AI re-engagement"},
        ],
    },
    "NESTLEIND": {
        "ticker": "NESTLEIND",
        "name": "Nestlé India",
        "theses": [
            {
                "version": 1,
                "date": "2022-01-10",
                "stance": "bullish",
                "author": "business_analyst",
                "evidence": ["Brand strength", "Rural recovery hope"],
                "confidence": 0.69,
                "outcome": "partially_correct",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2023-08-01",
                "stance": "neutral",
                "author": "committee",
                "evidence": ["Input cost pressure", "INR weakness"],
                "confidence": 0.6,
                "outcome": "correct",
                "overwritten": False,
            },
        ],
        "analyst_opinions": [
            {
                "version": 1,
                "date": "2023-08-01",
                "role": "financial",
                "opinion": "Margin pressure from imported inflation",
                "reasoning": "Oil/agri/INR chain",
                "evidence": ["CIG oil→FMCG", "FIL cost notes"],
                "confidence": 0.72,
                "uncertainty": ["Rural heal pace"],
                "accuracy": 0.77,
                "overwritten": False,
            }
        ],
        "committee_decisions": [
            {
                "version": 1,
                "date": "2023-08-05",
                "consensus": "neutral",
                "minority": "bullish brand premium",
                "vote": {"bullish": 2, "neutral": 4, "bearish": 1},
                "challenges": ["Valuation premium vs growth"],
                "evidence": ["PIL FMCG peers", "IKG supply chain"],
                "open_questions": ["When do gross margins expand?"],
                "decision": "Neutral quality hold suitability",
                "review_date": "2024-08-05",
                "outcome_quality": 0.75,
                "overwritten": False,
            }
        ],
        "forecasts": [
            {
                "version": 1,
                "date": "2022-01-10",
                "distribution": {"bull": 0.28, "base": 0.4, "bear": 0.2, "stress": 0.06, "recovery": 0.06},
                "most_likely": "base",
                "actual_outcome": "bear",
                "calibration": 0.5,
                "learning": "Underweighted INR/oil imported-inflation path",
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2023-08-01",
                "distribution": {"bull": 0.16, "base": 0.44, "bear": 0.24, "stress": 0.08, "recovery": 0.08},
                "most_likely": "base",
                "actual_outcome": "base",
                "calibration": 0.8,
                "learning": "Macro transmission better integrated",
                "overwritten": False,
            },
        ],
        "management": [
            {
                "version": 1,
                "date": "2023-08-01",
                "guidance_credibility": 0.78,
                "capital_allocation": "conservative",
                "execution": "steady",
                "leadership_change": False,
                "notes": "Premiumisation strategy consistent",
                "overwritten": False,
            }
        ],
        "decisions": [
            {
                "version": 1,
                "date": "2023-08-05",
                "question": "Is Nestlé India premium justified through cost shock?",
                "evidence": ["CIG", "FIL costs", "PIO concentration"],
                "reasoning": "Brand durable; near-term margins pressured",
                "alternatives": ["Prefer HUL", "Wait for oil decline"],
                "decision": "Neutral quality suitability",
                "confidence": 0.63,
                "outcome": "correct",
                "lessons": ["FMCG bull cases need commodity/INR triggers"],
                "overwritten": False,
            }
        ],
        "confidence_history": [
            {"date": "2022-01-10", "confidence": 0.69, "reason": "Brand premium", "evidence_improvements": [], "missing_evidence": ["Input cost path"]},
            {"date": "2023-08-01", "confidence": 0.6, "reason": "Imported inflation", "evidence_improvements": ["CIG chains"], "missing_evidence": ["Rural volume confirmation"]},
        ],
        "evidence_history": [
            {"date": "2022-01-10", "items": ["Brand segment notes"], "retained": True},
            {"date": "2023-08-01", "items": ["Oil/INR transmission", "FIL cost commentary"], "retained": True},
        ],
        "mistakes": [
            {
                "id": "m_nestle_2022_macro",
                "date": "2022-09-01",
                "context": "Oil/INR shock underweighted",
                "error_type": "macro_error",
                "example": "Unexpected oil / INR imported-inflation shock",
                "expected": "base",
                "observed": "bear",
                "lesson": "Always attach commodity/INR triggers to FMCG bulls",
            },
            {
                "id": "m_nestle_2022_evidence",
                "date": "2022-10-15",
                "context": "Cost note in filing underweighted initially",
                "error_type": "evidence_error",
                "example": "Important filing cost commentary underweighted",
                "expected": "stable margins",
                "observed": "compression",
                "lesson": "FIL cost notes are first-class evidence for FMCG",
            },
        ],
        "lessons": [
            {
                "date": "2023-08-05",
                "expected": "Base volumes/margins",
                "observed": "Margin pressure",
                "difference": "Macro transmission stronger than assumed",
                "reason": "Macro + evidence errors",
                "lesson": "Wire CIG/IKG commodity paths into FIE FMCG priors",
                "updated_knowledge": "Nestlé theses require oil/INR trigger matrix",
            }
        ],
        "company_timeline": [
            {"date": "2022-01", "domain": "business", "note": "Bullish brand thesis"},
            {"date": "2022-09", "domain": "macro", "note": "Oil/INR lesson"},
            {"date": "2023-08", "domain": "committee", "note": "Neutral stance"},
        ],
    },
}

PORTFOLIO_MEMORY: dict[str, dict[str, Any]] = {
    "agib_core_india": {
        "portfolio_id": "agib_core_india",
        "name": "AGIB Core India",
        "rebalances": [
            {
                "version": 1,
                "date": "2023-04-01",
                "action": "initiated_quality_bank_overweight_suitability",
                "allocation_note": "HDFC Bank suitability constructive",
                "expected_outcome": "quality compounding",
                "actual_outcome": "mixed — funding-cost drag",
                "performance_attribution": {"selection": 0.2, "timing": -0.4, "interaction": -0.1},
                "overwritten": False,
            },
            {
                "version": 2,
                "date": "2024-07-01",
                "action": "reduced_active_bank_tilt_to_neutral",
                "allocation_note": "Lesson from forecast miss",
                "expected_outcome": "lower drawdown in funding stress",
                "actual_outcome": "improved relative stability",
                "performance_attribution": {"selection": 0.1, "timing": 0.3, "interaction": 0.05},
                "overwritten": False,
            },
        ],
        "watchlist_changes": [
            {"date": "2024-06-22", "ticker": "KOTAKBANK", "change": "added_for_suitability_review", "overwritten": False},
            {"date": "2025-11-12", "ticker": "HDFCBANK", "change": "upgraded_review_priority", "overwritten": False},
        ],
        "mistakes": [
            {
                "id": "m_port_2023_conc",
                "date": "2023-10-01",
                "error_type": "portfolio_error",
                "example": "Concentration / correlation to rates underestimated",
                "lesson": "PIO stress scenarios must bind to FIE bank bear mass",
            }
        ],
        "lessons": [
            {
                "date": "2024-07-01",
                "lesson": "Allocation changes should reference ILM forecast calibration, not price narratives",
                "success_rate": 0.62,
                "repeated_errors": ["Ignoring liability-cycle timing"],
            }
        ],
    }
}


def get_company(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    row = CORPUS.get(t)
    return deepcopy(row) if row else None


def company_ids() -> list[str]:
    return sorted(CORPUS.keys())


def get_portfolio(portfolio_id: str) -> dict[str, Any] | None:
    pid = (portfolio_id or "").strip() or "agib_core_india"
    row = PORTFOLIO_MEMORY.get(pid)
    return deepcopy(row) if row else None


def list_portfolios() -> list[str]:
    return sorted(PORTFOLIO_MEMORY.keys())


def append_learning(ticker: str, lesson: dict[str, Any]) -> dict[str, Any]:
    """Append-only learning update — never overwrites prior rows."""
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    if t not in CORPUS:
        return {"accepted": False, "reason": "unknown_ticker", "ticker": t}
    lesson = dict(lesson)
    lesson.setdefault("date", lesson.get("date") or "2026-07-26")
    lesson.setdefault("overwritten", False)
    CORPUS[t].setdefault("lessons", []).append(lesson)
    # optional mistake append
    if lesson.get("mistake"):
        m = dict(lesson["mistake"])
        m.setdefault("date", lesson["date"])
        m.setdefault("id", f"m_{t.lower()}_{len(CORPUS[t].get('mistakes') or [])+1}")
        CORPUS[t].setdefault("mistakes", []).append(m)
    return {
        "accepted": True,
        "ticker": t,
        "lessons_count": len(CORPUS[t].get("lessons") or []),
        "append_only": True,
        "overwritten": False,
    }
