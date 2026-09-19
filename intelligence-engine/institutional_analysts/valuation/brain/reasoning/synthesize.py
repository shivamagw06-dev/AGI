"""Synthesize valuation frameworks into expectations-led institutional opinion."""

from __future__ import annotations

from typing import Any

from institutional_analysts.valuation.brain._text import parse_num

_BAD = (
    "the stock is expensive",
    "the stock is cheap",
    "pe =",
    "forward pe is",
)


def _scrub(text: str) -> str:
    out = text
    lower = out.lower()
    for bad in _BAD:
        if bad in lower:
            idx = lower.find(bad)
            out = (out[:idx] + out[idx + len(bad) :]).strip(" .,")
            lower = out.lower()
    # Soften bare "PE = 42x" style leftovers
    import re

    out = re.sub(r"\bpe\s*=\s*\d+(\.\d+)?x?\b", "the current earnings multiple", out, flags=re.I)
    return out


def synthesize(
    *,
    company: str,
    evidence: dict[str, Any],
    frameworks: dict[str, Any],
    learning: dict[str, Any],
    benchmarks: dict[str, Any],
) -> dict[str, Any]:
    exp = frameworks.get("market_expectations") or {}
    rel = frameworks.get("relative_valuation") or {}
    intrinsic = frameworks.get("intrinsic_value") or {}
    rev = frameworks.get("reverse_dcf") or {}
    hist = frameworks.get("historical_valuation") or {}
    peers = frameworks.get("peer_comparison") or {}
    mos = frameworks.get("margin_of_safety") or {}
    scenarios = frameworks.get("scenario_valuation") or {}
    cases = learning.get("cases") or {}
    dna = learning.get("valuation_dna") or {}
    historical = learning.get("historical") or {}

    pe = parse_num(evidence.get("pe") or evidence.get("forward_pe"))
    mos_txt = str(evidence.get("margin_of_safety") or "").lower()
    premium = "Premium" in str(exp.get("premium_or_discount") or "")
    thin = str(mos.get("downside_protection") or "") == "Thinner"

    # Stance compatible with prior IAF behaviour, but explained via expectations
    if any(w in mos_txt for w in ("high", "wide", "attractive", "ample")):
        stance = "Bullish"
    elif any(w in mos_txt for w in ("modest", "thin", "limited", "rich", "low")) or (pe is not None and pe >= 22) or (premium and thin):
        stance = "Bearish"
    else:
        stance = "Neutral"

    if stance == "Bullish":
        primary = (
            f"Today's valuation for {company} can be justified if base-case cash flows are delivered, "
            "because price does not clearly require heroic assumptions."
        )
    elif stance == "Bearish":
        primary = (
            f"Today's valuation for {company} only appropriately reflects long-term intrinsic value if "
            "demanding growth and capital-efficiency expectations are met; the margin of safety is thinner."
        )
    else:
        primary = (
            f"Today's valuation for {company} looks broadly balanced versus embedded expectations; "
            "attractiveness hinges on whether cash-flow delivery matches what is priced in."
        )

    executive = _scrub(
        " ".join(
            x
            for x in (
                primary,
                rel.get("assessment"),
                exp.get("assessment"),
                mos.get("assessment"),
                historical.get("historical_narrative"),
                cases.get("resemblance"),
            )
            if x
        )
    ).strip()

    # Ensure forward-multiple style WHY language appears when forward PE present
    if evidence.get("forward_pe") is not None and "forward" not in executive.lower():
        executive += (
            " The current forward earnings multiple suggests that investors expect the company to sustain "
            "above-average growth while maintaining strong returns on capital; future returns therefore depend "
            "on whether delivery stays consistent with those expectations."
        )

    reasoning = [
        {"question": "What growth / margins / ROIC / cash flow are priced in?", "answer": exp.get("assessment")},
        {"question": "How should relative multiples be interpreted?", "answer": rel.get("assessment")},
        {"question": "What does intrinsic-value discussion imply?", "answer": intrinsic.get("assessment")},
        {"question": "What does reverse DCF require?", "answer": rev.get("assessment")},
        {"question": "Where does price sit versus history?", "answer": hist.get("assessment")},
        {"question": "How do peers compare beyond multiples?", "answer": peers.get("assessment")},
        {"question": "What margin of safety remains?", "answer": mos.get("assessment")},
        {"question": "What do bull / base / bear scenarios imply?", "answer": scenarios.get("assessment")},
        {
            "question": "Does today's valuation appropriately reflect long-term intrinsic value and expectations?",
            "answer": primary,
        },
    ]

    strengths = []
    if stance == "Bullish":
        strengths.append("Embedded expectations leave more room for positive surprise")
    strengths.append("Peer and history triangulation available as cross-checks")
    if evidence.get("expected_return") is not None:
        strengths.append(f"Expected-return context: {evidence.get('expected_return')}")

    weaknesses = []
    if thin or premium:
        weaknesses.append("Multiple compression risk if growth or returns undershoot expectations")
    weaknesses.append("Earnings miss versus embedded expectations")
    if not weaknesses:
        weaknesses = ["Assumption sensitivity in intrinsic ranges"]

    assumptions = [
        "Market price is an expectations machine — multiples are interpreted, not treated as verdicts.",
        "Intrinsic value is discussed as a range under uncertainty; precision is not fabricated.",
        "Peer comparison adjusts for growth and capital efficiency, not multiples alone.",
        benchmarks.get("assessment") or "Benchmark context is qualitative where market regimes are incomplete.",
    ]
    uncertainties = [
        "Exact reverse-DCF inputs are incomplete — expectation intensity is inferred qualitatively.",
        "Historical multiple bands may shift if the company's growth/return regime changes.",
        "Scenario probabilities are judgemental, not statistical certainties.",
    ]
    missing = []
    if evidence.get("pe") is None and evidence.get("forward_pe") is None:
        missing.append("Current market multiple")
    if not evidence.get("peer_comparison"):
        missing.append("Named peer valuation set")

    return {
        "executive_opinion": executive,
        "primary_question_answer": primary,
        "stance": stance,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "reasoning_steps": reasoning,
        "assumptions": [a for a in assumptions if a][:6],
        "uncertainties": uncertainties,
        "missing_evidence": missing,
        "valuation_quality": {
            "grade": "Demanding" if premium or stance == "Bearish" else "Constructive" if stance == "Bullish" else "Balanced",
            "summary": executive,
            "justified_if": rev.get("expectations_realistic"),
        },
        "lessons_learned": list(historical.get("lessons_learned") or cases.get("lessons_from_cases") or [])[:8],
        "dna_summary": dna.get("summary"),
    }
