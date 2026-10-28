"""Generate institutional report blueprint before research begins."""

from __future__ import annotations

from typing import Any

_BLUEPRINTS: dict[str, list[str]] = {
    "Investment Evaluation": [
        "Executive Summary",
        "Investment Thesis",
        "Business Quality",
        "Financial Quality",
        "Valuation",
        "Risks",
        "Forecast",
        "Portfolio Fit",
        "Committee View",
        "Conclusion",
    ],
    "Valuation Assessment": [
        "Executive Summary",
        "Valuation Framework",
        "Multiples Analysis",
        "Intrinsic Value",
        "Peer Context",
        "Conclusion",
    ],
    "Historical Analysis": [
        "Executive Summary",
        "Historical Valuation Series",
        "Percentile Positioning",
        "Drivers of Re-rating",
        "Sector / Macro Context",
        "Conclusion",
    ],
    "Peer Comparison": [
        "Executive Summary",
        "Peer Universe",
        "Business Comparison",
        "Financial Comparison",
        "Valuation Comparison",
        "Relative Ranking",
        "Conclusion",
    ],
    "Educational": [
        "Concept Definition",
        "Why It Matters",
        "How To Calculate / Apply",
        "Worked Example",
        "Common Pitfalls",
        "Further Reading",
    ],
    "Macro Impact": [
        "Executive Summary",
        "Macro Impulse",
        "Transmission Channels",
        "Sector Implications",
        "Company-Level Effects",
        "Forecast Paths",
        "Conclusion",
    ],
    "Portfolio Decision": [
        "Mandate & Constraints",
        "Opportunity Set",
        "Proposed Allocation",
        "Risk Budget",
        "Implementation",
        "Monitoring Plan",
        "Committee Recommendation",
    ],
    "Risk Assessment": [
        "Risk Summary",
        "Market Risks",
        "Idiosyncratic Risks",
        "Stress Scenarios",
        "Mitigants",
        "Conclusion",
    ],
    "Forecast": [
        "Forecast Summary",
        "Base Case",
        "Key Drivers",
        "Sensitivities",
        "Risks to Forecast",
        "Conclusion",
    ],
    "Scenario Analysis": [
        "Scenario Map",
        "Base Case",
        "Bull Case",
        "Bear Case",
        "Probabilities",
        "Portfolio Implications",
    ],
    "Screening": [
        "Screen Criteria",
        "Universe Definition",
        "Filtered Results",
        "Shortlist Rationale",
        "Next Steps",
    ],
    "Sector Attractiveness": [
        "Sector Snapshot",
        "Demand & Cycle",
        "Competitive Structure",
        "Valuation Backdrop",
        "Attractiveness Score",
        "Conclusion",
    ],
    "Business Quality Assessment": [
        "Franchise Overview",
        "Moat Assessment",
        "Capital Allocation",
        "Quality Score",
        "Conclusion",
    ],
    "Financial Health Assessment": [
        "Health Summary",
        "Profitability",
        "Balance Sheet",
        "Cash Flow",
        "Red Flags",
        "Conclusion",
    ],
}


def generate_blueprint(
    primary_objective: str | None,
    *,
    expected_output: str | None = None,
) -> dict[str, Any]:
    sections = list(
        _BLUEPRINTS.get(
            primary_objective or "",
            [
                "Executive Summary",
                "Analysis",
                "Evidence",
                "Risks",
                "Conclusion",
            ],
        )
    )
    return {
        "blueprint": [{"order": i + 1, "section": s} for i, s in enumerate(sections)],
        "blueprint_sections": sections,
        "section_count": len(sections),
        "expected_output": expected_output,
        "map_version": "roe-v1",
    }
