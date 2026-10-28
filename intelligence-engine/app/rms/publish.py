"""Publishing adapters — website/newsletter/LinkedIn/archive stubs + KIP/predictions."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Literal

from app.rms.models import PublicationArtifact, ResearchObject


Channel = Literal["website", "newsletter", "linkedin", "internal_archive"]


def build_publication_artifacts(
    obj: ResearchObject,
    *,
    channels: list[Channel],
) -> list[PublicationArtifact]:
    body = obj.draft_body or obj.request_brief or obj.idea_summary
    thesis = ""
    if obj.reasoning_package:
        synth = obj.reasoning_package.get("synthesis") or {}
        thesis = str(synth.get("investment_thesis") or "")
    text = body or thesis or obj.title
    arts: list[PublicationArtifact] = []
    for ch in channels:
        if ch == "website":
            arts.append(
                PublicationArtifact(
                    channel="website",
                    title=obj.title,
                    body=text,
                    url=f"/research/{obj.research_id}",
                    status="created",
                )
            )
        elif ch == "newsletter":
            arts.append(
                PublicationArtifact(
                    channel="newsletter",
                    title=f"AGI Newsletter — {obj.title}",
                    body=_newsletter_body(obj, text),
                    status="created",
                )
            )
        elif ch == "linkedin":
            arts.append(
                PublicationArtifact(
                    channel="linkedin",
                    title=obj.title,
                    body=_linkedin_draft(obj, text),
                    status="draft",
                )
            )
        elif ch == "internal_archive":
            arts.append(
                PublicationArtifact(
                    channel="internal_archive",
                    title=f"ARCHIVE {obj.title}",
                    body=text,
                    url=f"archive://rms/{obj.research_id}/v{obj.version}",
                    status="archived",
                )
            )
    return arts


def kip_ingest_payload(obj: ResearchObject) -> dict[str, Any]:
    """Build AGI article ingest payload for KIP (no CMS redesign)."""
    synth = (obj.reasoning_package or {}).get("synthesis") or {}
    body_parts = [
        "Investment Thesis",
        str(synth.get("investment_thesis") or obj.idea_summary or ""),
        "Counter Thesis",
        str(synth.get("counter_thesis") or ""),
        "Catalysts",
        "\n".join(f"- {c}" for c in (synth.get("catalysts") or [])),
        "Risks",
        "\n".join(f"- {r}" for r in (synth.get("risks") or [])),
        "Valuation",
        str(synth.get("valuation_summary") or ""),
        "Draft",
        obj.draft_body or obj.request_brief,
    ]
    return {
        "title": obj.title,
        "content": "\n\n".join(p for p in body_parts if p),
        "author": obj.owner or "AGI",
        "source": "agi",
        "document_type": "agi_research",
        "tickers": list(obj.tickers),
        "themes": list(obj.themes),
        "sectors": list(obj.sectors),
        "article_id": obj.research_id,
        "research_type": "agi_research",
        "time_horizon": obj.prediction_horizon,
        "date": (_dt.date.today()).isoformat(),
        "metadata": {
            "rms_research_id": obj.research_id,
            "rms_version": obj.version,
            "reasoning_id": obj.reasoning_id,
        },
    }


def _newsletter_body(obj: ResearchObject, text: str) -> str:
    tickers = ", ".join(obj.tickers) if obj.tickers else "Multi-asset"
    return (
        f"AGI Research Digest\n"
        f"Coverage: {tickers}\n\n"
        f"{obj.title}\n\n"
        f"{text[:1200]}"
    )


def _linkedin_draft(obj: ResearchObject, text: str) -> str:
    tickers = " ".join(f"${t}" for t in obj.tickers[:5])
    return (
        f"{obj.title}\n\n"
        f"{text[:400]}\n\n"
        f"{tickers}\n"
        f"— Agarwal Global Investments (draft)"
    )
