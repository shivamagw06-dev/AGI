"""RMS dashboard aggregations."""

from __future__ import annotations

from app.rms.models import (
    PipelineCounts,
    ResearchObject,
    ResearchStatus,
    RmsDashboard,
)


def build_dashboard(rows: list[ResearchObject]) -> RmsDashboard:
    counts = PipelineCounts()
    for r in rows:
        attr = r.status.value
        if hasattr(counts, attr):
            setattr(counts, attr, getattr(counts, attr) + 1)

    draft_queue = [r.research_id for r in rows if r.status == ResearchStatus.DRAFT]
    review_queue = [
        r.research_id
        for r in rows
        if r.status
        in {
            ResearchStatus.INTERNAL_REVIEW,
            ResearchStatus.COMPLIANCE_REVIEW,
            ResearchStatus.REVISION_REQUESTED,
        }
    ]

    calendar = []
    for r in rows:
        if r.status == ResearchStatus.PUBLISHED and r.published_at:
            calendar.append(
                {
                    "research_id": r.research_id,
                    "title": r.title,
                    "published_at": r.published_at.isoformat(),
                    "tickers": r.tickers,
                }
            )
        elif r.status == ResearchStatus.APPROVED:
            calendar.append(
                {
                    "research_id": r.research_id,
                    "title": r.title,
                    "scheduled": "pending_publish",
                    "tickers": r.tickers,
                }
            )
    calendar.sort(key=lambda x: x.get("published_at") or "9999", reverse=True)

    pred_tracker = []
    for r in rows:
        if r.prediction_ids or r.status == ResearchStatus.PUBLISHED:
            pred_tracker.append(
                {
                    "research_id": r.research_id,
                    "title": r.title,
                    "tickers": r.tickers,
                    "prediction_horizon": r.prediction_horizon,
                    "prediction_ids": r.prediction_ids,
                    "status": r.status.value,
                }
            )

    company: dict[str, int] = {}
    sector: dict[str, int] = {}
    for r in rows:
        for t in r.tickers:
            company[t.upper()] = company.get(t.upper(), 0) + 1
        for s in r.sectors:
            sector[s] = sector.get(s, 0) + 1

    coverage = {
        "total_research": len(rows),
        "published": counts.published,
        "in_review": counts.internal_review + counts.compliance_review,
        "drafts": counts.draft,
        "ideas": counts.idea + counts.research_request,
    }

    return RmsDashboard(
        research_pipeline=counts,
        draft_queue=draft_queue,
        review_queue=review_queue,
        publication_calendar=calendar[:50],
        prediction_tracker=pred_tracker[:50],
        research_coverage=coverage,
        company_coverage=dict(sorted(company.items(), key=lambda kv: (-kv[1], kv[0]))),
        sector_coverage=dict(sorted(sector.items(), key=lambda kv: (-kv[1], kv[0]))),
        totals={
            "research_objects": len(rows),
            "draft_queue": len(draft_queue),
            "review_queue": len(review_queue),
            "published": counts.published,
        },
    )
