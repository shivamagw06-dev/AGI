from institutional_analysts.business.brain.reasoning.synthesize import synthesize

# V1-compatible shim
def reason(*, company: str, frameworks: dict, evidence: dict, previous: dict | None = None) -> dict:
    from institutional_analysts.business.brain.benchmarks import benchmark
    from institutional_analysts.business.brain.scoring import score_dimensions

    scoring = score_dimensions(frameworks, evidence)
    benches = benchmark(evidence, frameworks)
    out = synthesize(
        company=company,
        frameworks=frameworks,
        scoring=scoring,
        benchmarks=benches,
        previous=previous,
    )
    # Map to V1 keys
    return {
        "institutional_business_opinion": out["executive_opinion"],
        "business_quality": {
            "grade": scoring.get("grade"),
            "summary": out["executive_opinion"],
            "improving": (frameworks.get("moat") or {}).get("trajectory") == "Improving",
            "value_creation": out.get("capital_allocation_summary"),
            "dimensions": scoring.get("dimensions"),
            "exceptional_business": scoring.get("exceptional_business"),
            "ownership_bar": scoring.get("ownership_bar"),
        },
        "moat_assessment": frameworks.get("moat"),
        "competitive_outlook": (frameworks.get("competitive_outlook") or {}).get("why_improving_or_not"),
        "stance": out["stance"],
        "strengths": out["strengths"],
        "weaknesses": out["weaknesses"],
        "reasoning_steps": out["reasoning_steps"],
        "assumptions": out["assumptions"],
        "uncertainty": out["uncertainties"],
        "unanswered_questions": out["missing_evidence"]
        or [
            "Is market share actually increasing, or is industry growth lifting everyone?",
            "How durable is pricing power through the next competitive cycle?",
        ],
        "view_changes": out["view_changes"],
        "primary_question_answer": out["primary_question_answer"],
        "v2": out,
        "scoring": scoring,
        "benchmarks": benches,
    }


__all__ = ["synthesize", "reason"]
