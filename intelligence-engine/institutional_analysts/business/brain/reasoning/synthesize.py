"""Synthesize framework outputs into institutional business reasoning."""

from __future__ import annotations

from typing import Any


_BAD_PHRASES = (
    "good company",
    "strong company",
    "nice moat",
    "the company manufactures",
    "the company is a",
    "leading company",
)


def _scrub_lazy(text: str) -> str:
    out = text
    lower = out.lower()
    for bad in _BAD_PHRASES:
        if bad in lower:
            # Soft rewrite cue — remove lazy phrase occurrences
            idx = lower.find(bad)
            out = (out[:idx] + out[idx + len(bad) :]).strip(" .,")
            lower = out.lower()
    return out


def synthesize(
    *,
    company: str,
    frameworks: dict[str, Any],
    scoring: dict[str, Any],
    benchmarks: dict[str, Any],
    previous: dict[str, Any] | None = None,
    learning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    moat = frameworks.get("moat") or {}
    bm = frameworks.get("business_model") or {}
    customers = frameworks.get("customer_economics") or {}
    capital = frameworks.get("capital_allocation") or {}
    growth = frameworks.get("growth") or {}
    pricing = frameworks.get("pricing_power") or {}
    risks = frameworks.get("risks") or {}
    porter = frameworks.get("porter_five_forces") or {}
    chain = frameworks.get("value_chain") or {}
    mgmt = frameworks.get("management") or {}
    learn = learning if isinstance(learning, dict) else {}
    cases = learn.get("cases") if isinstance(learn.get("cases"), dict) else {}
    archetype = learn.get("archetype") if isinstance(learn.get("archetype"), dict) else {}
    historical = learn.get("historical") if isinstance(learn.get("historical"), dict) else {}
    dna = learn.get("business_dna") if isinstance(learn.get("business_dna"), dict) else {}

    grade = scoring.get("grade") or "Adequate"
    exceptional = bool(scoring.get("exceptional_business"))
    durability = str(moat.get("durability") or "Medium")
    hist_note = str(historical.get("trajectory_note") or "")
    softening = "no longer strengthening" in hist_note.lower() or "softening" in str(
        historical.get("quality_trend") or ""
    ).lower()

    # Softening trajectory is expressed in prose — not an automatic stance downgrade.
    # A durable high-quality franchise can remain an ownership candidate while no longer strengthening.
    if exceptional or grade in {"Exceptional", "High"}:
        stance = "Bullish"
    elif grade == "Weak" or durability in {"Weak", "Declining"}:
        stance = "Bearish"
    else:
        stance = "Neutral"

    executive = _scrub_lazy(
        (moat.get("assessment") or "")
        + " "
        + (capital.get("what_creates_long_term_returns") or capital.get("assessment") or "")
    ).strip()
    if not executive:
        executive = (
            f"{company}'s ownership case rests on whether franchise advantages compound returns "
            "above the opportunity cost of capital through the cycle."
        )

    hist_narrative = str(historical.get("historical_narrative") or "").strip()
    resemblance = str(cases.get("resemblance") or "").strip()
    arch_line = str(archetype.get("template_reasoning") or "").strip()

    # Institutional learning overlay — trajectory-aware, case-informed
    if hist_narrative and ("no longer strengthening" in hist_narrative.lower() or softening):
        executive = _scrub_lazy(f"{hist_narrative} {executive}").strip()
    elif hist_narrative:
        executive = _scrub_lazy(f"{executive} {hist_narrative}").strip()
    if resemblance:
        executive = _scrub_lazy(f"{executive} {resemblance}").strip()

    # Ensure primary question is answered explicitly
    if stance == "Bullish":
        if softening:
            ownership = (
                f"Yes — a long-term institutional investor would still want to own {company} on business grounds, "
                "while recognising the moat is durable but no longer strengthening as it did historically."
            )
        else:
            ownership = (
                f"Yes — a long-term institutional investor would want to own {company} on business grounds. "
                f"{executive or 'Franchise economics support durable compounding when execution remains disciplined.'}"
            )
    elif stance == "Bearish":
        ownership = (
            f"No — on present evidence, {company} does not yet clear the bar as an exceptional business "
            "worthy of long-term institutional ownership on quality alone."
        )
    else:
        ownership = (
            f"Not yet decisive — {company} is a credible franchise, but the file does not yet prove "
            "exceptional business quality with sufficient durability and improvement evidence."
        )

    executive_opinion = _scrub_lazy(f"{ownership} {executive}").strip()

    reasoning_steps = [
        {"question": "Why does this business create value?", "answer": bm.get("why_it_creates_value") or bm.get("assessment")},
        {"question": "Why are customers loyal?", "answer": customers.get("why_customers_are_loyal") or customers.get("assessment")},
        {
            "question": "Why can competitors not copy it?",
            "answer": moat.get("why_competitors_cannot_copy") or moat.get("replicability"),
        },
        {
            "question": "What creates long-term returns?",
            "answer": capital.get("what_creates_long_term_returns") or capital.get("assessment"),
        },
        {
            "question": "Which historical outcomes shape the current view?",
            "answer": hist_narrative or "No seeded multi-year path; relying on case and archetype lessons.",
        },
        {
            "question": "Which case analogues apply?",
            "answer": resemblance
            or f"Success analogue: {cases.get('primary_success_analogue')}; "
            f"counter-case: {cases.get('primary_failure_analogue')}.",
        },
        {
            "question": "What archetype pattern is this?",
            "answer": arch_line or (archetype.get("primary") or {}).get("name"),
        },
        {
            "question": "What is the Business DNA?",
            "answer": dna.get("summary"),
        },
        {
            "question": "Would a long-term institutional investor want to own this business?",
            "answer": ownership,
        },
        {
            "question": "How does industry structure affect attractiveness?",
            "answer": porter.get("implication") or porter.get("industry_attractiveness"),
        },
    ]

    assumptions = [
        "Assembled franchise, competitive and capital-allocation signals represent current operating reality.",
        "Advantage sources remain relevant over a multi-year ownership horizon.",
        "No abrupt regulatory or technological break permanently resets industry structure.",
        benchmarks.get("relative_positioning")
        or "Peer comparisons are directionally informative even when named peer sets are incomplete.",
        "Case analogues and archetypes are directional pattern guides, not identity claims.",
    ]
    for lesson in list(historical.get("lessons_learned") or [])[:2]:
        if lesson and lesson not in assumptions:
            assumptions.append(f"Lesson carried forward: {lesson}")

    uncertainties = [
        "Share gains versus industry growth may still be incompletely separated.",
        "Pricing power through the next competitive cycle is only partly observable.",
        "Return on incremental capital through stress periods needs continued confirmation.",
        "Management communication artefacts may be thinner than a full primary-file review.",
    ]

    missing = []
    if not bm.get("completed"):
        missing.append("Business model detail")
    if not pricing.get("completed"):
        missing.append("Direct pricing-power evidence")
    if not capital.get("completed"):
        missing.append("Capital allocation history detail")
    if not (growth.get("growth_drivers") or []):
        missing.append("Growth runway drivers")
    if "Limited direct management" in str(mgmt.get("communication") or ""):
        missing.append("Management communication artefacts")

    strengths = list(moat.get("sources") or [])[:4]
    for d in bm.get("revenue_streams") or []:
        if d not in strengths and len(strengths) < 5:
            strengths.append(d)

    weaknesses = list(risks.get("primary_risks") or [])[:4]

    view_changes = []
    if previous:
        prev_stance = previous.get("stance")
        if prev_stance and prev_stance != stance:
            view_changes.append(f"Business stance moved from {prev_stance} to {stance}.")
        prev_moat = None
        if isinstance(previous.get("moat_assessment"), dict):
            prev_moat = previous["moat_assessment"].get("durability")
        elif isinstance(previous.get("moat"), dict):
            prev_moat = previous["moat"].get("durability")
        if prev_moat and prev_moat != durability:
            view_changes.append(f"Moat durability revised from {prev_moat} to {durability}.")

    return {
        "executive_opinion": executive_opinion,
        "primary_question_answer": ownership,
        "stance": stance,
        "strengths": strengths,
        "weaknesses": weaknesses or ["Competition", "Execution", "Regulatory change"],
        "reasoning_steps": reasoning_steps,
        "assumptions": [a for a in assumptions if a][:6],
        "uncertainties": uncertainties,
        "missing_evidence": missing,
        "view_changes": view_changes,
        "business_model_summary": bm.get("assessment"),
        "revenue_drivers": bm.get("revenue_streams") or [],
        "customer_economics_summary": customers.get("assessment"),
        "pricing_power_summary": pricing.get("assessment"),
        "capital_allocation_summary": capital.get("assessment"),
        "innovation_summary": growth.get("technology"),
        "industry_position_summary": (
            f"{porter.get('industry_attractiveness')}. {benchmarks.get('assessment')}"
        ).strip(),
        "growth_runway_summary": growth.get("runway") or growth.get("assessment"),
        "competitive_position_summary": (
            f"{moat.get('summary') or moat.get('assessment')} "
            f"Value-chain locus: {chain.get('assessment')}"
        ).strip(),
        "opportunities": list(growth.get("growth_drivers") or [])[:5],
        "risks_list": list(risks.get("primary_risks") or [])[:6],
        "management_summary": mgmt.get("assessment"),
        "lessons_learned": list(historical.get("lessons_learned") or [])[:8],
        "case_resemblance": resemblance,
        "archetype_name": (archetype.get("primary") or {}).get("name"),
        "historical_narrative": hist_narrative,
        "business_dna_summary": dna.get("summary"),
    }
