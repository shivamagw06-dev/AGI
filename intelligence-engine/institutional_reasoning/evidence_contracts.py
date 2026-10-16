"""Phase 1 — Evidence Contracts (execution governance, not a new engine).

Each question type declares:
  * required evidence      — frameworks cannot execute without it
  * optional evidence      — strengthens, never gates
  * forbidden claims       — language that may not reach editorial unsupported

Architecture v1.0.1 LOCKED — soft helper under institutional_reasoning.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

CONTRACTS_VERSION = "evidence-contracts-v1.0.0"

# Canonical question types (deterministic classification target)
QUESTION_TYPES = (
    "education",
    "valuation",
    "business_quality",
    "financial_quality",
    "comparison",
    "investment_decision",
    "portfolio",
    "macro",
    "sector",
    "risk",
    "forecast",
)

# Types that bypass live evidence execution entirely (Academy path).
EDUCATION_TYPES = frozenset({"education"})


@dataclass(frozen=True)
class EvidenceContract:
    question_type: str
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    requires_entity: bool = True
    entity_confidence_threshold: float = 0.7
    version: str = CONTRACTS_VERSION
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_UNSUPPORTED_VALUATION_WORDS = (
    "expensive",
    "cheap",
    "fair",
    "overvalued",
    "undervalued",
    "attractively valued",
    "rich",
    "bargain",
)

CONTRACTS: dict[str, EvidenceContract] = {
    "education": EvidenceContract(
        question_type="education",
        required=(),
        optional=("academy_concepts", "academy_frameworks"),
        forbidden_claims=("buy", "sell", "target price"),
        requires_entity=False,
        notes="Academy Books path — no live market evidence required.",
    ),
    "valuation": EvidenceContract(
        question_type="valuation",
        required=("current_pe", "historical_pe", "historical_percentile", "peer_pe"),
        optional=("peg", "dividend_yield", "ev_ebitda", "price_to_book"),
        forbidden_claims=_UNSUPPORTED_VALUATION_WORDS,
        notes="No expensive/cheap/fair language unless required evidence executed.",
    ),
    "business_quality": EvidenceContract(
        question_type="business_quality",
        required=("roic", "margins", "revenue_quality", "competitive_position"),
        optional=("market_share", "switching_costs", "pricing_power"),
        forbidden_claims=("wide moat", "no moat", "high quality", "low quality"),
    ),
    "financial_quality": EvidenceContract(
        question_type="financial_quality",
        required=("cash_conversion", "leverage", "earnings_quality"),
        optional=("working_capital", "accruals", "interest_cover"),
        forbidden_claims=("strong balance sheet", "weak balance sheet"),
    ),
    "comparison": EvidenceContract(
        question_type="comparison",
        required=("peer_set", "comparable_metrics"),
        optional=("peer_percentile", "relative_growth"),
        forbidden_claims=("better than", "worse than", "outperform", "underperform"),
    ),
    "investment_decision": EvidenceContract(
        question_type="investment_decision",
        required=(
            "current_pe",
            "historical_percentile",
            "downside_case",
            "expected_return",
        ),
        optional=("catalysts", "portfolio_fit", "liquidity"),
        forbidden_claims=("buy", "sell", "hold", "target price", "accumulate"),
    ),
    "portfolio": EvidenceContract(
        question_type="portfolio",
        required=("exposure", "risk_contribution"),
        optional=("correlation", "beta", "tracking_error", "crowding"),
        forbidden_claims=("suitable", "unsuitable", "increase allocation"),
    ),
    "macro": EvidenceContract(
        question_type="macro",
        required=("macro_series", "policy_stance"),
        optional=("transmission_path", "historical_analogue"),
        forbidden_claims=("recession confirmed", "rate cut guaranteed"),
        requires_entity=False,
        entity_confidence_threshold=0.0,
    ),
    "sector": EvidenceContract(
        question_type="sector",
        required=("sector_metrics", "sector_history"),
        optional=("sector_peer_set", "demand_signal"),
        forbidden_claims=("best sector", "avoid sector"),
    ),
    "risk": EvidenceContract(
        question_type="risk",
        required=("downside_case", "risk_drivers"),
        optional=("stress_scenario", "volatility"),
        forbidden_claims=("safe", "risk-free", "no downside"),
    ),
    "forecast": EvidenceContract(
        question_type="forecast",
        required=("driver_assumptions", "scenario_set"),
        optional=("sensitivity", "calibration_history"),
        forbidden_claims=("will rise", "will fall", "guaranteed"),
    ),
}


def contract_for(question_type: str) -> EvidenceContract:
    return CONTRACTS.get(str(question_type or "").lower()) or CONTRACTS["valuation"]


# ---------------------------------------------------------------------------
# Deterministic question classification
# ---------------------------------------------------------------------------

_EDU_PATTERNS = (
    re.compile(r"^\s*(what|who|define|explain|meaning of|difference between)\b", re.I),
    re.compile(r"\bwhat\s+(is|are|does)\b", re.I),
    re.compile(r"\b(how\s+(do|does)\s+.*\s+work|formula for)\b", re.I),
)

_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "investment_decision",
        re.compile(
            r"\b(should (i|we) (buy|sell|invest)|worth buying|good investment|entry point|"
            r"invest [£$₹]|£[\d,]+|million in)\b",
            re.I,
        ),
    ),
    (
        "valuation",
        re.compile(
            r"\b(expensive|cheap|overvalued|undervalued|fair value|intrinsic|"
            r"p/?e\b|pe ratio|ev/?ebitda|price to book|multiple[s]?\b|percentile|"
            r"relative valuation|using relative valuation|"
            r"should dcf|dcf be used|dcf applicable|dcf wrong|invalidates dcf|"
            r"which framework dominates|framework dominate)\b|"
            r"^\s*value\b",
            re.I,
        ),
    ),
    (
        "comparison",
        re.compile(
            r"\b(compare|compared|comparison|versus|vs\.?|against|better than|which is|which multiple|"
            r"graham vs|buffett and damodaran|disagreement)\b",
            re.I,
        ),
    ),
    (
        "business_quality",
        re.compile(
            r"\b(moat|business quality|quality business|competitive|roic|pricing power|"
            r"market share|capital allocation|reinvestment|franchise|"
            r"buffett reject|wonderful business)\b",
            re.I,
        ),
    ),
    (
        "financial_quality",
        re.compile(
            r"\b(cash flow|cash conversion|balance sheet|leverage|debt|earnings quality|"
            r"accruals?|working capital|receivables?|inventory|piotroski|altman|beneish|"
            r"asset turnover)\b",
            re.I,
        ),
    ),
    ("portfolio", re.compile(r"\b(portfolio|position siz|weight|exposure|allocation|overweight|underweight)\b", re.I)),
    ("macro", re.compile(r"\b(macro|inflation|gdp|rbi|fed|interest rate|monetary|fiscal|rupee|currency)\b", re.I)),
    # "sector cap"/"sector limit" is a portfolio constraint, not sector research.
    ("sector", re.compile(r"\b(?!sector\s+(cap|limit|constraint|exposure|weight))(sector|industry)\b", re.I)),
    ("risk", re.compile(r"\b(risk|downside|threat|drawdown|vulnerab)\b", re.I)),
    ("forecast", re.compile(r"\b(forecast|outlook|next year|project|estimate|will\b)\b", re.I)),
)


def classify_question(question: str) -> dict[str, Any]:
    """Deterministic type + confidence. Education detected before market types."""
    q = str(question or "").strip()
    if not q:
        return {"question_type": "education", "confidence": 0.3, "reason": "empty_question"}

    matched: list[str] = []
    for qtype, pattern in _TYPE_PATTERNS:
        if pattern.search(q):
            matched.append(qtype)

    # Education wins unless the question names a real entity (company/index/sector).
    is_education_shape = any(p.search(q) for p in _EDU_PATTERNS)
    has_entity_hint = any(pattern.search(q) for pattern, *_ in _KNOWN_ENTITIES)
    if is_education_shape and not matched:
        return {"question_type": "education", "confidence": 0.93, "reason": "definition_shape"}
    if is_education_shape and matched and not has_entity_hint:
        # e.g. "What is ROIC?" / "What is PE ratio?" — concept question about a metric
        return {"question_type": "education", "confidence": 0.86, "reason": "concept_about_metric"}

    if matched:
        primary = matched[0]
        confidence = 0.9 if len(matched) == 1 else 0.8
        return {
            "question_type": primary,
            "confidence": confidence,
            "reason": "pattern_match",
            "candidates": matched[:4],
        }

    return {"question_type": "investment_decision", "confidence": 0.5, "reason": "default_research"}


# ---------------------------------------------------------------------------
# Entity resolution (deterministic index/company map + soft ERE fallback)
# ---------------------------------------------------------------------------

_KNOWN_ENTITIES: tuple[tuple[re.Pattern[str], str, str, str], ...] = (
    (re.compile(r"\bnifty\s*it\b|\bniftyit\b", re.I), "NIFTYIT", "Nifty IT", "Index"),
    (re.compile(r"\bbank\s*nifty\b|\bnifty\s*bank\b", re.I), "NIFTYBANK", "Nifty Bank", "Index"),
    (re.compile(r"\bnifty\s*50\b|\bnifty50\b", re.I), "NIFTY50", "Nifty 50", "Index"),
    (re.compile(r"\bnifty\b", re.I), "NIFTY50", "Nifty 50", "Index"),
    (re.compile(r"\bsensex\b", re.I), "SENSEX", "BSE Sensex", "Index"),
    (re.compile(r"\binfosys\b|\binfy\b", re.I), "INFY", "Infosys", "Company"),
    (re.compile(r"\btcs\b|\btata consultancy\b", re.I), "TCS", "Tata Consultancy Services", "Company"),
    (re.compile(r"\bhcl\s*tech\b|\bhcltech\b", re.I), "HCLTECH", "HCL Technologies", "Company"),
    (re.compile(r"\btech\s*mahindra\b|\btechm\b", re.I), "TECHM", "Tech Mahindra", "Company"),
    (re.compile(r"\bwipro\b", re.I), "WIPRO", "Wipro", "Company"),
    (re.compile(r"\bhdfc\s*bank\b", re.I), "HDFCBANK", "HDFC Bank", "Company"),
    (re.compile(r"\bidbi(?:\s*bank(?:\s*ltd|\s*limited)?)?\b", re.I), "IDBI", "IDBI Bank", "Company"),
    (re.compile(r"\bicici\s*bank\b", re.I), "ICICIBANK", "ICICI Bank", "Company"),
    (re.compile(r"\baxis\s*bank\b", re.I), "AXISBANK", "Axis Bank", "Company"),
    (re.compile(r"\bkotak(?:\s*bank|\s*mahindra)?\b", re.I), "KOTAKBANK", "Kotak Mahindra Bank", "Company"),
    (re.compile(r"\bsbi\b|\bstate bank of india\b", re.I), "SBIN", "State Bank of India", "Company"),
    (re.compile(r"\breliance\b", re.I), "RELIANCE", "Reliance Industries", "Company"),
    (re.compile(r"\bmeta(?:\s+platforms)?\b|\bfacebook\b|\bfb\b", re.I), "META", "Meta Platforms", "Company"),
    (re.compile(r"\bapple\b|\baapl\b", re.I), "AAPL", "Apple", "Company"),
    (re.compile(r"\bmicrosoft\b|\bmsft\b", re.I), "MSFT", "Microsoft", "Company"),

    (re.compile(r"\bzomato\b|\beternal\b", re.I), "ZOMATO", "Zomato", "Company"),
    (re.compile(r"\bnestle(?:\s*india)?\b", re.I), "NESTLEIND", "Nestlé India", "Company"),
    (re.compile(r"\bhindustan\s*unilever\b|\bhul\b", re.I), "HINDUNILVR", "Hindustan Unilever", "Company"),
    (re.compile(r"\bbritannia\b", re.I), "BRITANNIA", "Britannia Industries", "Company"),
    (re.compile(r"\bdabur\b", re.I), "DABUR", "Dabur India", "Company"),
    (re.compile(r"\bitc\b", re.I), "ITC", "ITC Limited", "Company"),
    (re.compile(r"\basian\s*paints\b", re.I), "ASIANPAINT", "Asian Paints", "Company"),
    (re.compile(r"\bbajaj\s*finance\b", re.I), "BAJFINANCE", "Bajaj Finance", "Company"),
    (re.compile(r"\btitan\b", re.I), "TITAN", "Titan Company", "Company"),
    (re.compile(r"\btrent\b", re.I), "TRENT", "Trent", "Company"),
    (re.compile(r"\btata\s*power\b", re.I), "TATAPOWER", "Tata Power", "Company"),
    (re.compile(r"\bongc\b", re.I), "ONGC", "ONGC", "Company"),
    (re.compile(r"\badani\s*green\b", re.I), "ADANIGREEN", "Adani Green", "Company"),
)


def resolve_entities(
    question: str,
    *,
    ticker_hint: str | None = None,
    entity_resolution_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve primary entity deterministically; report confidence + candidates.

    When multiple entities appear (e.g. Infosys vs TCS), prefer the earliest
    mention in the question text — critical for comparison questions.
    """
    q = str(question or "")
    found: list[dict[str, Any]] = []
    for pattern, entity_id, name, etype in _KNOWN_ENTITIES:
        m = pattern.search(q)
        if m:
            found.append(
                {
                    "entity_id": entity_id,
                    "entity_name": name,
                    "entity_type": etype,
                    "confidence": 0.99,
                    "source": "deterministic_map",
                    "span_start": m.start(),
                }
            )
    # Prefer earliest span; de-dupe by entity_id
    found.sort(key=lambda f: int(f.get("span_start") or 0))
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for f in found:
        if f["entity_id"] in seen:
            continue
        seen.add(f["entity_id"])
        # strip internal span helper
        unique.append({k: v for k, v in f.items() if k != "span_start"})

    if not unique and isinstance(entity_resolution_pack, dict):
        ere = entity_resolution_pack.get("entity_resolution") or entity_resolution_pack
        cand = ere.get("entity") if isinstance(ere.get("entity"), dict) else None
        if cand and cand.get("entity_id"):
            unique.append(
                {
                    "entity_id": str(cand.get("entity_id")).upper(),
                    "entity_name": cand.get("canonical_name") or cand.get("entity_name"),
                    "entity_type": cand.get("entity_type") or "Unknown",
                    "confidence": float(cand.get("confidence") or 0.6),
                    "source": "entity_resolution_engine",
                }
            )

    if not unique and ticker_hint:
        unique.append(
            {
                "entity_id": str(ticker_hint).upper(),
                "entity_name": str(ticker_hint).upper(),
                "entity_type": "Unknown",
                "confidence": 0.55,
                "source": "ticker_hint",
            }
        )

    primary = unique[0] if unique else None
    # Comparison questions name two sides; expose the counterparty explicitly so
    # downstream consumers do not have to re-parse the candidate list.
    secondary = unique[1] if len(unique) > 1 else None
    return {
        "resolved": bool(primary),
        "primary": primary,
        "secondary": secondary,
        "counterparties": unique[1:6],
        "candidates": unique[:6],
        "ambiguous": len(unique) > 1,
        "confidence": float(primary.get("confidence")) if primary else 0.0,
    }


def clarification_required(
    classification: dict[str, Any],
    entities: dict[str, Any],
) -> dict[str, Any]:
    """Stop execution when the contract needs an entity we could not resolve."""
    qtype = str(classification.get("question_type") or "")
    contract = contract_for(qtype)
    if not contract.requires_entity:
        return {"required": False}
    conf = float(entities.get("confidence") or 0.0)
    if not entities.get("resolved") or conf < contract.entity_confidence_threshold:
        return {
            "required": True,
            "reason": "entity_unresolved_or_low_confidence",
            "entity_confidence": conf,
            "threshold": contract.entity_confidence_threshold,
            "message": (
                "Which company, index or sector should this analysis cover? "
                "Frameworks were not executed because the subject could not be resolved."
            ),
        }
    return {"required": False, "entity_confidence": conf}


def forbidden_claim_hits(text: str, question_type: str) -> list[str]:
    contract = contract_for(question_type)
    lowered = str(text or "").lower()
    return [w for w in contract.forbidden_claims if w in lowered]


def contract_dict(question_type: str) -> dict[str, Any]:
    return contract_for(question_type).to_dict()
