"""Step 4 — Research planning before retrieval."""

from __future__ import annotations

from app.irp.models import DomainType, ResearchPlan, ResearchPlanStep, ResolvedEntityPack


def build_research_plan(
    question: str,
    *,
    intent: str,
    domain: DomainType | str,
    entities: ResolvedEntityPack,
) -> ResearchPlan:
    focus = list(entities.tickers[:8])
    themes = list(entities.themes[:6])
    subject = entities.sector_label or entities.primary_ticker or "subject"
    base_q = (question or subject).strip()

    steps: list[ResearchPlanStep] = [
        ResearchPlanStep(
            order=1,
            source_class="agi_research",
            query=f"{base_q} AGI house view {subject}",
            rationale="Prioritise AGI institutional research first.",
        ),
        ResearchPlanStep(
            order=2,
            source_class="house_view",
            query=f"{subject} current house view",
            rationale="Establish AGI stance before external opinions.",
        ),
        ResearchPlanStep(
            order=3,
            source_class="broker_research",
            query=f"{subject} broker outlook",
            required=False,
            rationale="Surface sell-side consensus and disagreements.",
        ),
        ResearchPlanStep(
            order=4,
            source_class="company_filings",
            query=f"{subject} filings earnings",
            required=False,
            rationale="Ground the view in filings / results language.",
        ),
        ResearchPlanStep(
            order=5,
            source_class="macro",
            query=f"{subject} macro drivers {' '.join(entities.macro_drivers[:3])}",
            required=False,
            rationale="Link sector/company outcomes to macro drivers.",
        ),
        ResearchPlanStep(
            order=6,
            source_class="themes",
            query=f"{subject} themes {' '.join(themes)}",
            required=False,
            rationale="Pull related thematic evidence.",
        ),
        ResearchPlanStep(
            order=7,
            source_class="news",
            query=f"{subject} latest developments",
            required=False,
            rationale="Freshness overlay — only entity-relevant news.",
        ),
        ResearchPlanStep(
            order=8,
            source_class="predictions",
            query=f"{subject} prediction history",
            required=False,
            rationale="Track prior AGI calls where available.",
        ),
    ]
    if domain == "sector":
        steps.insert(
            2,
            ResearchPlanStep(
                order=2,
                source_class="sector_universe",
                query=f"{subject} leaders {' '.join(focus[:5])}",
                rationale="Map sector question onto the investable company universe.",
            ),
        )
        # re-number
        for i, step in enumerate(steps, start=1):
            step.order = i

    return ResearchPlan(
        intent=intent,
        domain=str(domain),
        steps=steps,
        focus_tickers=focus,
        focus_themes=themes,
        reject_topics=list(entities.reject_topics),
    )
