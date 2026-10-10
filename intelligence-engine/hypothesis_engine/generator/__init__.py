"""Hypothesis generator — produce specific, testable institutional theses."""

from __future__ import annotations

from typing import Any

from hypothesis_engine.quality_rules import enforce_quality
from hypothesis_engine.taxonomy import focus_types, owners_for


def _entity_label(entity: dict[str, Any] | None, question: str) -> str:
    ent = entity or {}
    return (
        str(ent.get("canonical_name") or ent.get("ticker") or "").strip()
        or _guess_name(question)
        or "the subject"
    )


def _guess_name(question: str) -> str:
    q = question.strip()
    for prefix in ("Should I buy ", "Should I sell ", "What are the risks in ", "Analyse ", "Analyze "):
        if q.startswith(prefix):
            return q[len(prefix) :].rstrip("?").strip()
    if " vs " in q.lower():
        return q
    if "nifty" in q.lower():
        for token in q.replace("?", "").split():
            if "nifty" in token.lower() or token.upper().startswith("NIFTY"):
                return token if "nifty" in token.lower() else f"Nifty {token}"
        return "Nifty IT" if "it" in q.lower() else "the index"
    return ""


def _peer_label(question: str, entity: dict[str, Any] | None) -> str:
    q = question.lower()
    if " vs " in q:
        parts = question.replace("?", "").split(" vs ")
        if len(parts) >= 2:
            return parts[1].strip()
    peers = (entity or {}).get("peers") or []
    if peers:
        p0 = peers[0]
        if isinstance(p0, dict):
            return str(p0.get("canonical_name") or p0.get("ticker") or "peers")
        return str(p0)
    # sector defaults
    name = _entity_label(entity, question).lower()
    if "bank" in name or "hdfc" in name or "icici" in name:
        return "ICICI Bank and Axis Bank"
    if "infosys" in name or "tcs" in name or "wipro" in name or "it" in name:
        return "Infosys / TCS peer set"
    return "closest listed peers"


def _templates_for(
    *,
    question: str,
    entity_name: str,
    peer: str,
    focus: list[str],
    primary_objective: str | None,
) -> list[dict[str, Any]]:
    q = question.lower()
    obj = (primary_objective or "").lower()
    out: list[dict[str, Any]] = []

    # Historical valuation / expensive vs history
    if "versus history" in q or "expensive" in q and "history" in q or "historical analysis" in obj:
        out.extend(
            [
                {
                    "type": "Valuation",
                    "statement": (
                        f"{entity_name} currently trades above its multi-year historical valuation range "
                        f"on forward multiples, implying limited room for further multiple expansion unless "
                        f"earnings growth accelerates versus history."
                    ),
                    "reason": "Historical percentile positioning is the core decision variable for this question.",
                    "confidence": 0.78,
                    "required_evidence": [
                        "10y PE/EV-EBITDA history",
                        "Current forward multiple",
                        "Historical percentile rank",
                    ],
                    "falsification": "False if current multiples sit at or below the 10-year median.",
                },
                {
                    "type": "Industry",
                    "statement": (
                        f"The current premium in {entity_name} reflects AI / growth optimism that is only "
                        f"partially supported by observable order books and near-term demand indicators."
                    ),
                    "reason": "Narrative premia often detach from near-term fundamentals.",
                    "confidence": 0.64,
                    "required_evidence": [
                        "Management commentary on AI/demand",
                        "Order book / deal wins",
                        "Peer premium comparison",
                    ],
                    "falsification": "False if peer-relative growth and bookings justify the premium.",
                },
                {
                    "type": "Macro",
                    "statement": (
                        f"US / global enterprise demand recovery relevant to {entity_name} is already priced "
                        f"into the sector multiple, so macro improvement alone is unlikely to expand valuations further."
                    ),
                    "reason": "Macro beta may already be embedded in price.",
                    "confidence": 0.61,
                    "required_evidence": [
                        "US ISM / IT spending indicators",
                        "Sector earnings revisions",
                        "Valuation vs macro cycles",
                    ],
                    "falsification": "False if multiples still sit below prior recovery peaks with rising revisions.",
                },
                {
                    "type": "Forecast",
                    "statement": (
                        f"Historical comparisons for {entity_name} suggest limited multiple expansion from here "
                        f"because earnings growth would need to exceed the upper quartile of prior cycles to re-rate."
                    ),
                    "reason": "Links valuation upside to an explicit growth threshold.",
                    "confidence": 0.69,
                    "required_evidence": [
                        "Consensus growth path",
                        "Prior-cycle growth vs re-rating map",
                        "Scenario multiples",
                    ],
                    "falsification": "False if base-case growth already exceeds prior upper-quartile outcomes.",
                },
            ]
        )
        return out

    # Comparison
    if "compare" in q or " vs " in q or "peer comparison" in obj:
        out.extend(
            [
                {
                    "type": "Competitive",
                    "statement": (
                        f"Relative business quality favors one side of ({entity_name}) because switching costs, "
                        f"pricing power, or distribution breadth create a durable competitive gap versus {peer} "
                        f"that should persist unless share trends converge."
                    ),
                    "reason": "Comparison decisions hinge on durable relative advantage.",
                    "confidence": 0.7,
                    "required_evidence": ["Moat evidence", "Market share trends", "Pricing power metrics"],
                    "falsification": "False if share and pricing trends converge for 3+ years.",
                },
                {
                    "type": "Financial",
                    "statement": (
                        f"Financial quality differentials (ROIC, cash conversion, leverage) between the compared "
                        f"names are large enough to justify a structural valuation gap rather than a temporary one, "
                        f"so the higher-ROIC name deserves the premium only if cash conversion stays superior."
                    ),
                    "reason": "Financial superiority must be cash-backed to matter.",
                    "confidence": 0.68,
                    "required_evidence": ["ROIC series", "FCF conversion", "Leverage / credit metrics"],
                    "falsification": "False if ROIC and FCF conversion converge within a narrow band.",
                },
                {
                    "type": "Valuation",
                    "statement": (
                        f"The cheaper name on peer-relative multiples does not offer true value if the discount "
                        f"exactly offsets weaker growth durability versus {peer}."
                    ),
                    "reason": "Cheapness without quality is not decision-relevant.",
                    "confidence": 0.66,
                    "required_evidence": ["Relative PE/EV", "Growth differentials", "Historical relative bands"],
                    "falsification": "False if the discount exceeds the growth/quality gap on a multi-year basis.",
                },
            ]
        )
        return out

    # Educational — fewer, concept-linked
    if "explain" in q or "what is" in q or "educational" in obj:
        concept = question.replace("Explain", "").replace("explain", "").replace("?", "").strip() or "the concept"
        out.append(
            {
                "type": "Financial",
                "statement": (
                    f"{concept} is decision-relevant because it isolates whether incremental capital earns "
                    f"returns above the cost of capital, and therefore whether growth creates or destroys value."
                ),
                "reason": "Educational questions still need a testable institutional claim.",
                "confidence": 0.8,
                "required_evidence": ["Definition/source", "Worked calculation", "Firm case study"],
                "falsification": "False if the metric can be high while economic value is destroyed after WACC.",
            }
        )
        return out

    # Portfolio
    if "portfolio" in q or "portfolio" in obj:
        out.extend(
            [
                {
                    "type": "Portfolio",
                    "statement": (
                        f"Adding exposure consistent with this request improves risk-adjusted portfolio quality "
                        f"only if correlation and drawdown contribution remain below the existing risk budget."
                    ),
                    "reason": "Portfolio decisions are constraint-relative, not stock-absolute.",
                    "confidence": 0.67,
                    "required_evidence": ["Current holdings covariance", "Risk budget", "Proposed weights"],
                    "falsification": "False if incremental volatility-adjusted contribution exceeds risk budget.",
                },
                {
                    "type": "Risk",
                    "statement": (
                        "Concentrated factor exposures (rates, growth, or credit) would dominate idiosyncratic "
                        "stock selection and therefore should bound position sizing before thesis strength does, "
                        "unless stress tests show stock-specific risk above factor risk."
                    ),
                    "reason": "Factor risk often dominates stock-level alpha in portfolios.",
                    "confidence": 0.63,
                    "required_evidence": ["Factor exposures", "Stress scenarios", "Sizing rules"],
                    "falsification": "False if stock-specific risk dominates factor risk in stress tests.",
                },
            ]
        )
        return out

    # Macro
    if "rbi" in q or "macro" in obj or "rate cut" in q:
        out.extend(
            [
                {
                    "type": "Macro",
                    "statement": (
                        "Policy easing transmits to the sector primarily through funding costs and credit demand, "
                        "so the investment implication depends on whether NIM compression is offset by volume growth "
                        "rather than a blanket re-rating of all banks."
                    ),
                    "reason": "Macro impact must specify the transmission channel.",
                    "confidence": 0.72,
                    "required_evidence": ["Rate path", "NIM sensitivity", "Credit growth data"],
                    "falsification": "False if historical easing cycles show NIM gains without volume offsets.",
                },
                {
                    "type": "Industry",
                    "statement": (
                        "Competitive intensity will determine which banks capture incremental credit demand after "
                        "rate cuts, so sector beta alone is an incomplete investment thesis unless loan growth "
                        "diverges across peers."
                    ),
                    "reason": "Winners within the sector matter more than the average.",
                    "confidence": 0.65,
                    "required_evidence": ["Loan growth by bank", "Deposit franchise quality", "Pricing behaviour"],
                    "falsification": "False if loan growth and spreads move uniformly across peers.",
                },
                {
                    "type": "Forecast",
                    "statement": (
                        "Near-term earnings revisions for rate-sensitive names will turn before multiples expand, "
                        "making revision momentum a leading test of the macro investment thesis relative to history."
                    ),
                    "reason": "Links macro to a falsifiable market path.",
                    "confidence": 0.6,
                    "required_evidence": ["Earnings revision series", "Multiple path in prior cycles"],
                    "falsification": "False if multiples expand while revisions are still negative.",
                },
            ]
        )
        return out

    # Default investment evaluation (HDFC Bank style)
    out.extend(
        [
            {
                "type": "Business",
                "statement": (
                    f"{entity_name} possesses a durable funding / franchise advantage that sustains superior "
                    f"deposit mix and pricing power versus {peer} because switching costs and distribution "
                    f"density reduce customer attrition."
                ),
                "reason": "Business quality is the foundation of a long-term buy case.",
                "confidence": 0.82,
                "required_evidence": [
                    "Deposit mix / CASA trends",
                    "Franchise metrics vs peers",
                    "Customer attrition / stickiness evidence",
                ],
                "falsification": "False if CASA and deposit cost advantages compress to peer median for 2+ years.",
            },
            {
                "type": "Valuation",
                "statement": (
                    f"Current valuation of {entity_name} already reflects that franchise quality, so expected "
                    f"returns depend more on multiple mean-reversion risk than on further quality discovery."
                ),
                "reason": "Quality without margin of safety is not a buy thesis.",
                "confidence": 0.63,
                "required_evidence": [
                    "Current PE/PB vs history",
                    "Peer-relative premium",
                    "Implied growth in price",
                ],
                "falsification": "False if valuation sits below historical median on like-for-like growth.",
            },
            {
                "type": "Forecast",
                "statement": (
                    f"Deposit or volume growth at {entity_name} may slow over the next two years as system "
                    f"liquidity and competitive intensity normalise, reducing earnings growth versus recent run-rates."
                ),
                "reason": "Forward path is a distinct testable claim from current quality.",
                "confidence": 0.58,
                "required_evidence": [
                    "Deposit growth history",
                    "System liquidity indicators",
                    "Management guidance",
                ],
                "falsification": "False if deposit growth sustains above cycle average for 4+ quarters.",
            },
            {
                "type": "Financial",
                "statement": (
                    f"Credit costs / asset quality at {entity_name} remain structurally benign relative to peers "
                    f"because underwriting standards and secured mix keep steady-state credit cost below mid-cycle "
                    f"sector averages."
                ),
                "reason": "Financial durability must be separated separately from franchise narrative.",
                "confidence": 0.71,
                "required_evidence": [
                    "GNPA/NNPA trends",
                    "Credit cost history",
                    "Segment mix (secured vs unsecured)",
                ],
                "falsification": "False if credit costs rise to or above peer mid-cycle averages.",
            },
            {
                "type": "Competitive",
                "statement": (
                    f"Competition from {peer} is narrowing historical advantages in deposits, digital acquisition, "
                    f"or loan growth, which would compress the justified valuation premium over time."
                ),
                "reason": "Competitive convergence is a primary thesis risk.",
                "confidence": 0.66,
                "required_evidence": [
                    "Peer deposit/loan growth",
                    "Digital acquisition metrics",
                    "Relative NIM / fee trends",
                ],
                "falsification": "False if advantage metrics widen for 2+ consecutive years.",
            },
            {
                "type": "Risk",
                "statement": (
                    f"Regulatory, funding, or concentration risks could invalidate the buy case for {entity_name} "
                    f"even if near-term earnings remain solid, because those risks are not fully visible in run-rate ROE."
                ),
                "reason": "Risk hypotheses must be explicit before research begins.",
                "confidence": 0.6,
                "required_evidence": [
                    "Regulatory actions / capital rules",
                    "Funding concentration",
                    "Stress loss estimates",
                ],
                "falsification": "False if capital, funding, and concentration metrics stay comfortably above thresholds.",
            },
            {
                "type": "Portfolio",
                "statement": (
                    f"Adding {entity_name} improves portfolio risk-adjusted quality only if it diversifies existing "
                    f"financials / rate factor exposure rather than concentrating the same macro beta."
                ),
                "reason": "Buy decisions are portfolio-relative for institutional capital.",
                "confidence": 0.57,
                "required_evidence": ["Current portfolio factor map", "Correlation to financials", "Sizing constraints"],
                "falsification": "False if incremental factor concentration falls after inclusion.",
            },
        ]
    )

    # Filter to focus types when possible, keep order
    focused = [h for h in out if h["type"] in focus]
    return focused or out


def generate_hypotheses(
    *,
    question: str,
    entity: dict[str, Any] | None = None,
    primary_objective: str | None = None,
    required_analysts: list[str] | None = None,
) -> list[dict[str, Any]]:
    focus = focus_types(primary_objective, question)
    name = _entity_label(entity, question)
    peer = _peer_label(question, entity)
    raw = _templates_for(
        question=question,
        entity_name=name,
        peer=peer,
        focus=focus,
        primary_objective=primary_objective,
    )

    hypotheses: list[dict[str, Any]] = []
    for i, item in enumerate(raw, start=1):
        owners = owners_for(item["type"])
        if required_analysts:
            # prefer intersection but keep taxonomy owners
            inter = [a for a in owners if a in required_analysts]
            if inter:
                owners = inter
        hyp = {
            "id": f"H{i}",
            "statement": item["statement"],
            "reason": item["reason"],
            "type": item["type"],
            "confidence": float(item["confidence"]),
            "required_evidence": list(item["required_evidence"]),
            "responsible_analysts": owners,
            "priority": i,
            "status": "proposed",
            "falsification_test": item.get("falsification"),
            "assumptions": {
                "known": [f"Entity under review is {name}"],
                "unknown": ["Path of competitive response", "Near-term macro surprises"],
                "weak": ["Implied growth embedded in price may be misestimated"],
                "evidence_gaps": [],
            },
        }
        hyp = enforce_quality(hyp)
        if hyp.get("quality_compliant"):
            hypotheses.append(hyp)

    # Re-number after filtering
    for i, hyp in enumerate(hypotheses, start=1):
        hyp["id"] = f"H{i}"
        hyp["priority"] = i
    return hypotheses
