"""Next Best Research Question — highest-value next activity with reason."""

from __future__ import annotations

from typing import Any

from research_workflow_framework.schema import STATUS_COMPLETE, STATUS_NEEDS_REVIEW, STATUS_PENDING


def next_best_research_question(
    *,
    workflow: dict[str, Any],
    research_status: dict[str, Any],
    ticker: str | None,
    company: str | None,
) -> dict[str, Any]:
    """Determine highest-value next research activity."""
    label = company or ticker or "this company"
    items = research_status.get("items") or []

    target = next((i for i in items if i.get("status") == STATUS_NEEDS_REVIEW), None)
    if not target:
        target = next((i for i in items if i.get("status") == STATUS_PENDING), None)

    if not target:
        return {
            "question": f"What would invalidate the investment thesis on {label}?",
            "reason": "Core workflow steps are complete — thesis stress testing is the highest-value next activity.",
            "activity": "Thesis Stress Test",
        }

    activity = target.get("label") or "Research"
    pk = target.get("playbook_key") or ""

    prompts: dict[str, tuple[str, str]] = {
        "Business Quality": (
            f"Assess {label}'s business quality and competitive advantage",
            "Institutional research begins with whether the franchise is durable before valuation or timing.",
        ),
        "Financial Quality": (
            f"Review {label}'s financial strength, cash conversion, and balance sheet resilience",
            "Business quality must translate into financial quality before an investment view can form.",
        ),
        "Management": (
            f"How does {label}'s management allocate capital and execute strategy?",
            "Capital allocation and execution often explain long-term value creation or destruction.",
        ),
        "Valuation": (
            f"Is {label} expensive relative to its own history, growth, and closest peers?",
            "Current valuation is inconclusive without historical and relative context.",
        ),
        "Risks": (
            f"What could materially impair the investment case for {label}?",
            "Risk assessment clarifies what could invalidate today's research view.",
        ),
        "Peer Comparison": (
            f"How does {label} compare with its closest peer on quality, growth, and valuation?",
            "Relative valuation may materially change the research conclusion when absolute valuation is inconclusive.",
        ),
        "Portfolio Fit": (
            f"Does {label} fit my portfolio concentration, correlation, and risk budget?",
            "Opportunity cost and portfolio context determine whether research converts to action.",
        ),
        "Thesis Stress Test": (
            f"What evidence would invalidate today's thesis on {label}?",
            "Institutional investors define invalidation criteria before acting on research.",
        ),
        "Thesis Review": (
            f"Has the investment thesis on {label} changed materially?",
            "Thesis evolution determines whether prior research remains relevant.",
        ),
    }

    if activity in prompts:
        question, reason = prompts[activity]
    elif pk == "peer_comparison":
        question = f"How does {label} compare with its closest peer on valuation and growth?"
        reason = "Relative comparison may resolve inconclusive absolute valuation."
    elif pk == "valuation_assessment":
        question = f"Is {label} expensive relative to history and peers?"
        reason = "Valuation context is required before the research conclusion can firm up."
    else:
        question = f"Continue institutional research on {label}: {activity}"
        reason = f"{activity} is the next incomplete step in this workflow."

    if target.get("status") == STATUS_NEEDS_REVIEW:
        reason = f"{activity} was reviewed but needs further evidence — {reason}"

    return {
        "question": question,
        "reason": reason,
        "activity": activity,
        "playbook_key": pk,
    }
