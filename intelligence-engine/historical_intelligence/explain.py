"""Module 5 — Historical Explainability.

Every historical answer closes the same four questions: what changed, why it
mattered, what evidence was used, and over what window — plus a confidence that
comes from coverage rather than from how much text was produced.

The "why" here is deliberately restrained. The warehouse holds observations, not
causes, so this layer draws the inference the evidence supports and names the
association rather than asserting causation it cannot demonstrate.
"""

from __future__ import annotations

from typing import Any, Optional

CONFIDENCE_SENTENCES = {
    "strong": "Confidence is high: a long, dense series with few gaps.",
    "moderate": "Confidence is moderate: the series is usable but short or uneven.",
    "weak": "Confidence is low: too few observations to carry much weight.",
    "none": "No confidence can be attached — there is no observed history.",
}


def _why_it_mattered(module: dict[str, Any]) -> Optional[str]:
    """The investor-relevant reading of the finding, tied to what was measured."""
    kind = module.get("module")
    metric = module.get("metric")

    if kind == "trend":
        cagr = module.get("cagr_pct")
        consistency = module.get("consistency_pct")
        inflections = module.get("inflection_points") or []
        if cagr is None:
            return None
        if metric in ("revenue", "pat", "ebitda", "eps"):
            if consistency is not None and consistency >= 75:
                return (
                    f"Compounding of {cagr}% with {consistency}% of periods moving the same way is "
                    "the signature of a business scaling rather than one recovering — the kind of "
                    "record that usually earns a durable multiple."
                )
            return (
                f"Growth of {cagr}% arrived unevenly"
                + (f", turning around {inflections[0]}" if inflections else "")
                + ", so the trajectory matters more to a forecast than the average does."
            )
        if metric in ("roe", "roce", "net_margin", "ebitda_margin"):
            direction = "improving" if cagr > 0 else "deteriorating"
            return (
                f"A {direction} return profile changes what the business is worth independently of "
                "growth, because it changes how much capital each rupee of profit consumes."
            )
        if metric in ("debt", "debt_equity"):
            return (
                "Leverage direction sets how much of the equity story is financial rather than "
                "operational, and how much room exists before the balance sheet constrains it."
            )
        if metric == "price":
            return (
                f"A {cagr}% annual return over the observed window is the shareholder outcome; "
                "whether it was earned by fundamentals or by re-rating is a separate question the "
                "valuation history answers."
            )
        return None

    if kind == "valuation":
        premium = module.get("premium_to_own_median_pct")
        rerating = module.get("rerating") or {}
        if premium is None:
            return None
        if rerating.get("direction") == "expansion":
            return (
                "The multiple expanded across the window, so part of any shareholder return came "
                "from the market paying more for the same earnings — a source of return that does "
                "not repeat indefinitely."
            )
        if rerating.get("direction") == "compression":
            return (
                "The multiple compressed across the window, meaning earnings had to work against "
                "a falling rating; if the business is unchanged, that is where value can appear."
            )
        if premium > 15:
            return (
                "Trading above its own history means the market is pricing in improvement, so the "
                "risk sits with delivery rather than with the rating."
            )
        if premium < -15:
            return (
                "Trading below its own history means either the market expects less than it used "
                "to, or the rating has not caught up with the business — the two need separating."
            )
        return "Sitting near its own median, the rating is not itself the argument either way."

    if kind == "extreme":
        return (
            "Extremes only mean something against a full record; measured inside a short window "
            "they describe recent positioning, not long-run value."
        )

    if kind == "events":
        return (
            "Events dated against price show what the market did around each announcement, which "
            "is where a pattern of distribution or dilution becomes visible."
        )

    if kind == "comparison":
        return (
            "Restricting the comparison to the shared window keeps it a statement about the "
            "businesses rather than about which one AGIB happens to hold more history for."
        )

    if kind == "period":
        change = module.get("change_pct")
        if change is None:
            return None
        return (
            "How a business priced through a stress episode is evidence about its perceived "
            "durability, which is hard to observe in calm periods."
        )
    return None


def explain(module: dict[str, Any]) -> dict[str, Any]:
    """Attach the closing block every historical answer must carry."""
    coverage = module.get("coverage") or {}
    guard = module.get("guard") or {}
    confidence = module.get("confidence") or coverage.get("confidence") or "none"

    evidence: list[dict[str, Any]] = []
    if coverage.get("tab"):
        evidence.append({
            "source": f"warehouse.{coverage['tab']}",
            "metric": coverage.get("metric"),
            "observations": coverage.get("observations"),
            "window": coverage.get("window_label"),
        })
    for extra in module.get("extra_evidence") or []:
        evidence.append(extra)

    limits: list[str] = []
    if guard.get("verdict") in ("partial_window", "outside_window", "no_data"):
        limits.append(guard.get("disclosure") or "")
    if not guard.get("full_history_claim_allowed", False) and coverage.get("observations"):
        limits.append(
            "No claim is made about periods outside the observed window."
        )
    if coverage.get("gap_count"):
        biggest = (coverage.get("gaps") or [{}])[0]
        if biggest.get("days"):
            limits.append(
                f"The series has {coverage['gap_count']} gap(s); the largest is "
                f"{biggest['days']} days between {biggest.get('from')} and {biggest.get('to')}."
            )

    return {
        "what_changed": module.get("finding"),
        "why_it_mattered": _why_it_mattered(module),
        "evidence": evidence,
        "observation_window": module.get("observation_window") or coverage.get("window_label"),
        "confidence": confidence,
        "confidence_score": coverage.get("confidence_score"),
        "confidence_note": CONFIDENCE_SENTENCES.get(confidence, ""),
        "limits": [line for line in limits if line],
    }
