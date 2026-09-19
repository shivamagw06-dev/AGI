"""Uncertainty Guard — Institutional Accounting Exam Section J
("Impossible Questions").

The single most important behavior this module enforces: **when the
evidence is insufficient to attribute a single cause, say so — and list
the genuinely plausible alternatives — rather than inventing one.**

This is deliberately NOT a rule-firing engine like ``rule_library``.
Those rules only fire when TWO metrics' actual deltas are known and
compared. This guard exists for the opposite case: when a question
gives just ONE fact (e.g. "PAT doubled — what happened?") with no
supporting context at all, and the only honest answer is to refuse a
single-cause attribution.
"""

from __future__ import annotations

from typing import Any, Optional

# Genuinely plausible, non-exhaustive-but-representative alternative causes
# per target metric — used ONLY to demonstrate the range of explanations,
# never to pick a "most likely" one without evidence.
PLAUSIBLE_CAUSES: dict[str, list[str]] = {
    "pat_change": [
        "margin expansion (higher gross or EBITDA margin)",
        "a lower effective tax rate",
        "lower interest expense (debt repayment or refinancing)",
        "a one-time or non-operating gain",
        "revenue growth without a proportional cost increase",
        "a prior-period one-off loss that did not repeat",
    ],
    "revenue_change": [
        "volume growth",
        "pricing or realisation increase",
        "a favourable product/customer mix shift",
        "an acquisition consolidating new revenue",
        "a change in revenue recognition timing",
    ],
    "roe_change": [
        "improved net margin",
        "improved asset turnover",
        "a change in financial leverage",
        "a shrinking equity base from buybacks or dividends",
        "one-time gains inflating PAT in the period",
    ],
    "ebitda_change": [
        "revenue growth",
        "gross margin expansion",
        "operating expense reduction / cost discipline",
        "a change in accounting classification between COGS and OpEx",
        "a one-time cost reversal (e.g. provision write-back)",
    ],
    "cash_change": [
        "operating cash generation",
        "a financing event (new debt or equity raised)",
        "an investing event (asset sale or reduced capex)",
        "working capital release (collections, inventory reduction)",
        "a one-time item (litigation settlement, asset sale)",
    ],
    "margin_change": [
        "pricing power / realisation change",
        "input cost inflation or relief",
        "product or customer mix shift",
        "operating leverage from volume change",
        "a one-time cost or accounting reclassification",
    ],
}

# Minimum context needed before a single-cause attribution is responsible.
# These are illustrative categories of supporting evidence, not literal
# field names — the guard checks how many of these categories the caller
# has actually supplied.
REQUIRED_CONTEXT: dict[str, list[str]] = {
    "pat_change": ["revenue_trend", "margin_trend", "tax_rate_trend", "interest_trend", "one_off_items_flag"],
    "revenue_change": ["volume_data", "pricing_data", "mix_data", "acquisition_flag"],
    "roe_change": ["net_margin_trend", "asset_turnover_trend", "leverage_trend", "equity_base_trend"],
    "ebitda_change": ["revenue_trend", "gross_margin_trend", "opex_trend", "one_off_items_flag"],
    "cash_change": ["operating_cf_trend", "investing_cf_trend", "financing_cf_trend"],
    "margin_change": ["pricing_data", "input_cost_data", "mix_data", "volume_data"],
}


def assess_causal_sufficiency(
    target_metric: str, known_context: Optional[dict[str, Any]] = None, *, minimum_fraction: float = 0.5
) -> dict[str, Any]:
    """The core Section J behavior.

    ``known_context`` is whatever supporting evidence the question
    actually supplies (e.g. {"revenue_trend": "+5%"}). If fewer than
    ``minimum_fraction`` of the categories required to responsibly
    attribute a cause are present, refuse a single-cause answer and
    list the genuinely plausible alternatives instead.
    """
    known_context = known_context or {}
    causes = PLAUSIBLE_CAUSES.get(target_metric, [])
    required = REQUIRED_CONTEXT.get(target_metric, [])
    present = [k for k in required if k in known_context and known_context[k] is not None]
    fraction_present = (len(present) / len(required)) if required else 1.0
    sufficient = fraction_present >= minimum_fraction

    if sufficient:
        return {
            "sufficient_evidence": True,
            "target_metric": target_metric,
            "supporting_context_used": present,
            "note": "Sufficient supporting context is available — a grounded, evidence-based explanation "
            "should be constructed from it rather than this guard's generic alternative list.",
        }

    causes_text = ", ".join(causes[:4]) + (", etc." if len(causes) > 4 else "")
    answer = (
        f"There isn't enough information to determine the cause of the {target_metric.replace('_', ' ')}. "
        f"Several explanations are possible ({causes_text}), and additional evidence "
        f"(such as {', '.join(sorted(set(required) - set(present))[:3]) or 'revenue, margin, and cost detail'}) "
        f"is required to distinguish between them."
    )
    return {
        "sufficient_evidence": False,
        "target_metric": target_metric,
        "answer": answer,
        "plausible_causes": causes,
        "missing_context": sorted(set(required) - set(present)),
        "supporting_context_used": present,
        "hallucination_free": True,
    }


# Loose keyword stems (not exact phrases) used only to detect whether a
# candidate answer commits to a specific single cause — deliberately
# permissive since real answers phrase causes in many ways.
_CAUSE_KEYWORD_STEMS: dict[str, list[str]] = {
    "pat_change": ["margin", "tax", "interest", "one-time", "one-off", "gain", "expense"],
    "revenue_change": ["volume", "pricing", "price", "mix", "acquisition", "recognition"],
    "roe_change": ["margin", "turnover", "leverage", "buyback", "equity", "one-time", "one-off"],
    "ebitda_change": ["revenue", "margin", "opex", "cost", "reclassif", "provision"],
    "cash_change": ["operating", "financing", "investing", "working capital", "collection", "settlement"],
    "margin_change": ["pricing", "price", "input cost", "mix", "volume", "leverage", "reclassif"],
}

_CERTAINTY_MARKERS = (
    "because", "due to", "driven by", "caused by", "resulted from", "the reason", "this is because",
)


def is_single_cause_claim_overconfident(claim: str, target_metric: str, known_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Grading helper: does a candidate answer assert ONE specific cause
    with false confidence when the evidence doesn't support singling one
    out? Used to penalise hallucinated certainty in the exam grader."""
    assessment = assess_causal_sufficiency(target_metric, known_context)
    if assessment["sufficient_evidence"]:
        return {"overconfident": False, "reason": "sufficient evidence was available"}

    low = claim.lower()
    uncertainty_markers = (
        "isn't enough information", "is not enough information", "insufficient", "cannot be determined",
        "several explanations", "multiple explanations", "additional evidence", "not enough evidence",
        "several possible", "could be", "possible explanations", "not enough information",
    )
    admits_uncertainty = any(m in low for m in uncertainty_markers)
    keyword_hits = [kw for kw in _CAUSE_KEYWORD_STEMS.get(target_metric, []) if kw in low]
    asserts_certainty = any(m in low for m in _CERTAINTY_MARKERS)
    overconfident = (not admits_uncertainty) and (len(keyword_hits) >= 1) and (asserts_certainty or len(low) < 200)
    return {
        "overconfident": overconfident,
        "admits_uncertainty": admits_uncertainty,
        "single_cause_markers_found": len(keyword_hits),
        "keyword_hits": keyword_hits,
    }
