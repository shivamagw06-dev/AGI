"""Source-channel ingest adapters and retrieval priority helpers (KIP P1)."""

from __future__ import annotations

from app.kip.models import SOURCE_PRIORITY, DocumentType, IngestRequest


AGI_TYPES = {
    DocumentType.AGI_RESEARCH,
    DocumentType.AGI_NOTE,
    DocumentType.AGI_CIO_REPORT,
    DocumentType.AGI_DAILY_BRIEF,
    DocumentType.AGI_INVESTMENT_OFFICE,
    DocumentType.AGI_MODEL_PORTFOLIO,
}

BROKER_TYPES = {
    DocumentType.BROKER_RESEARCH,
    DocumentType.BROKER_EMAIL,
    DocumentType.STRATEGY_NOTE,
    DocumentType.SELL_SIDE,
    DocumentType.BUY_SIDE,
}

INTERNAL_TYPES = {
    DocumentType.AGI_NOTE,
    DocumentType.AGI_INVESTMENT_OFFICE,
    DocumentType.STRATEGY_NOTE,
}


def retrieval_priority(document_type: str | DocumentType) -> int:
    key = document_type.value if isinstance(document_type, DocumentType) else str(document_type)
    return SOURCE_PRIORITY.get(key, 7)


def source_class(document_type: str | DocumentType) -> str:
    key = document_type.value if isinstance(document_type, DocumentType) else str(document_type)
    p = SOURCE_PRIORITY.get(key, 7)
    if p == 1:
        return "agi_research"
    if p == 4:
        return "broker_research"
    if key == DocumentType.MARKET_NEWS.value:
        return "latest_news"
    if p == 6:
        return "company_filings"
    return "general_knowledge"


def normalize_agi_request(req: IngestRequest) -> IngestRequest:
    dtype = req.document_type if req.document_type in AGI_TYPES else DocumentType.AGI_RESEARCH
    research_type = req.research_type or dtype.value
    return req.model_copy(
        update={
            "source": "agi",
            "document_type": dtype,
            "research_type": research_type,
            "author": req.author or "AGI",
        }
    )


def normalize_broker_request(req: IngestRequest) -> IngestRequest:
    dtype = req.document_type if req.document_type in BROKER_TYPES else DocumentType.BROKER_RESEARCH
    return req.model_copy(
        update={
            "source": req.source or "broker",
            "document_type": dtype,
            "research_type": req.research_type or dtype.value,
        }
    )


def normalize_newsletter_request(req: IngestRequest) -> IngestRequest:
    return req.model_copy(
        update={
            "source": req.source or "newsletter",
            "document_type": DocumentType.NEWSLETTER,
            "research_type": req.research_type or "newsletter",
        }
    )


def normalize_internal_request(req: IngestRequest) -> IngestRequest:
    dtype = req.document_type if req.document_type in INTERNAL_TYPES else DocumentType.AGI_NOTE
    return req.model_copy(
        update={
            "source": req.source or "agi_internal",
            "document_type": dtype,
            "research_type": req.research_type or "internal_note",
            "author": req.author or "AGI Analyst",
        }
    )
