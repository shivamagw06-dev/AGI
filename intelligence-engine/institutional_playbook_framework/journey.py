"""Research Journey Map — institutional research progress tracking."""

from __future__ import annotations

from typing import Any

from institutional_playbook_framework.schema import JOURNEY_STEP_ALIASES


def infer_completed_step(
    *,
    playbook_key: str,
    question: str,
    playbook_selection: dict[str, Any] | None = None,
    response_sections: dict[str, Any] | None = None,
) -> str | None:
    """Infer which journey step this turn completes."""
    low = (question or "").lower()
    for alias, step in JOURNEY_STEP_ALIASES.items():
        if alias in low:
            return step

    sel = playbook_selection or {}
    name = str(sel.get("playbook_name") or sel.get("name") or "").lower()
    for alias, step in JOURNEY_STEP_ALIASES.items():
        if alias in name:
            return step

    sections = response_sections or {}
    if sections.get("valuation") or sections.get("valuation_assessment"):
        return "Valuation"
    if sections.get("business_quality"):
        return "Business Quality"
    if sections.get("financial_strength") or sections.get("financial_quality"):
        return "Financial Quality"
    if sections.get("risks"):
        return "Risks"
    if sections.get("research_conclusion"):
        return "Thesis Review"

    if "compare" in low or " vs " in low:
        return "Peer Comparison"
    if "portfolio" in low or "holdings" in low:
        return "Portfolio Fit"
    if playbook_key in {"valuation_assessment", "valuation"}:
        return "Valuation"
    if "expensive" in low or "cheap" in low or "valuation" in low:
        return "Valuation"
    if playbook_key in {"earnings_review"}:
        return "Financial Quality"
    if playbook_key in {"peer_comparison"}:
        return "Peer Comparison"
    if playbook_key in {"business_quality_assessment", "economic_moat"}:
        return "Business Quality"
    if playbook_key in {"investment_assessment"}:
        return "Investment Assessment"
    return None


def build_journey_map(
    *,
    journey_steps: list[str],
    completed_steps: list[str],
    ticker: str | None = None,
) -> dict[str, Any]:
    """Build progress map for UI."""
    steps = [s for s in journey_steps if s]
    completed = [s for s in completed_steps if s in steps]
    total = len(steps)
    done = len(completed)
    pct = int(round(100 * done / total)) if total else 0

    step_rows = []
    for step in steps:
        step_rows.append(
            {
                "label": step,
                "completed": step in completed,
                "current": step not in completed and (not completed or steps.index(step) == done),
            }
        )

    next_step = None
    for step in steps:
        if step not in completed and step != "Decision Complete":
            next_step = step
            break

    return {
        "ticker": ticker,
        "steps": step_rows,
        "completed_steps": completed,
        "progress_pct": pct,
        "progress_label": f"{done}/{total} steps",
        "next_step": next_step,
        "complete": "Decision Complete" in completed or done >= max(total - 1, 1),
    }


def suggest_next_research(
    *,
    journey_map: dict[str, Any],
    playbook: dict[str, Any],
    ticker: str | None = None,
) -> list[str]:
    """Institutional follow-up — next research step, not generic chat."""
    label = ticker or "this company"
    templates = list(playbook.get("follow_up_templates") or [])
    suggestions: list[str] = []

    next_step = journey_map.get("next_step")
    if next_step:
        step_prompts = {
            "Business Quality": f"Assess {label} business quality and competitive advantage",
            "Financial Quality": f"Review {label} financial strength and cash conversion",
            "Valuation": f"Is {label} expensive relative to history and peers?",
            "Growth": f"What drives {label} growth over the next 2–3 years?",
            "Risks": f"What could go wrong with {label}?",
            "Peer Comparison": f"Compare {label} with its closest peer",
            "Portfolio Fit": f"Does {label} fit my portfolio concentration and risk budget?",
            "Thesis Review": f"What would invalidate the {label} investment thesis?",
        }
        if next_step in step_prompts:
            suggestions.append(step_prompts[next_step])

    for tmpl in templates[:4]:
        suggestions.append(tmpl.format(ticker=label))

    # De-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for s in suggestions:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out[:6]
