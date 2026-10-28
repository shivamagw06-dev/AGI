"""KIP ingest pipeline — Document → … → Institutional Knowledge Base."""

from __future__ import annotations

from datetime import date

from app.kip.chunking import chunk_document
from app.kip.extractors import (
    apply_ocr,
    build_knowledge_metadata,
    clean_text,
    extract_document_metadata,
    extract_investment_metadata,
    extract_research_metadata,
    extractive_summary,
)
from app.kip.flags import KipFlags
from app.kip.graph import link_related_research, upsert_from_document
from app.kip.models import (
    DocumentType,
    IngestRequest,
    KipDocument,
    TimelineEvent,
)
from app.kip.store import KipStore

PIPELINE_STAGES = [
    "ocr",
    "document_cleaning",
    "metadata_extraction",
    "entity_resolution",
    "table_extraction",
    "financial_metric_extraction",
    "timeline_extraction",
    "theme_detection",
    "sector_detection",
    "company_linking",
    "risk_extraction",
    "catalyst_extraction",
    "valuation_extraction",
    "investment_thesis_extraction",
    "bull_case",
    "bear_case",
    "counter_arguments",
    "confidence",
    "chunking",
    "embeddings",
    "hybrid_search_index",
    "knowledge_graph",
    "house_view_update",
    "institutional_knowledge_base",
]


class KipPipeline:
    def __init__(self, store: KipStore, flags: KipFlags, *, embedding_dim: int = 256) -> None:
        self.store = store
        self.flags = flags
        self.embedding_dim = embedding_dim

    def ingest(self, request: IngestRequest) -> KipDocument:
        if not self.flags.kip:
            raise RuntimeError("KIP is disabled")

        stages: list[str] = []
        version = 1
        lineage_id = request.lineage_id
        supersedes = request.supersedes

        if self.flags.kip_versioning and supersedes:
            prev = self.store.get_document(supersedes)
            if prev is not None:
                lineage_id = prev.lineage_id
                version = prev.document.version + 1
        if lineage_id is None:
            # create new lineage via document factory defaults
            pass

        # OCR
        raw, ocr_applied = apply_ocr(
            request.content,
            needs_ocr=request.needs_ocr,
            ocr_text=request.ocr_text,
            ocr_enabled=self.flags.kip_ocr,
        )
        stages.append("ocr")

        cleaned = clean_text(raw)
        stages.append("document_cleaning")

        doc_meta = extract_document_metadata(
            title=request.title,
            author=request.author,
            source=request.source,
            document_type=request.document_type,
            broker=request.broker,
            language=request.language,
            doc_date=request.date,
            content=cleaned,
            version=version,
        )
        stages.append("metadata_extraction")

        investment = extract_investment_metadata(
            cleaned,
            tickers=request.tickers,
            companies=request.companies,
            themes=request.themes,
            sectors=request.sectors,
        )
        stages.extend(
            [
                "entity_resolution",
                "theme_detection",
                "sector_detection",
                "company_linking",
            ]
        )

        research = extract_research_metadata(cleaned)
        if request.expected_return:
            research.expected_return = request.expected_return
        if request.time_horizon:
            research.time_horizon = request.time_horizon
        stages.extend(
            [
                "table_extraction",
                "financial_metric_extraction",
                "timeline_extraction",
                "risk_extraction",
                "catalyst_extraction",
                "valuation_extraction",
                "investment_thesis_extraction",
                "bull_case",
                "bear_case",
                "counter_arguments",
            ]
        )

        summary = ""
        if self.flags.kip_llm_summary:
            summary = extractive_summary(cleaned, research)

        related = []
        if investment.tickers:
            for t in investment.tickers:
                related.extend(self.store.company_document_ids(t)[:8])
        related = sorted(set(related))

        knowledge = build_knowledge_metadata(
            source=request.source,
            doc_date=doc_meta.date,
            as_of=date.today(),
            research=research,
            investment=investment,
            related_documents=related,
            summary=summary,
        )
        # Prefer AGI related research links
        knowledge.related_research = [
            rid
            for rid in related
            if (d := self.store.get_document(rid)) is not None
            and d.document.document_type.value.startswith("agi_")
        ][:12]
        stages.append("confidence")

        # Auto-version AGI articles by article_id when supersedes not provided
        article_id = request.article_id
        if self.flags.kip_versioning and article_id and not supersedes:
            prior = self.store.get_by_article_id(article_id)
            if prior is not None and prior.superseded_by is None:
                supersedes = prior.document_id
                lineage_id = prior.lineage_id
                version = prior.document.version + 1

        doc = KipDocument(
            article_id=article_id,
            research_type=request.research_type or request.document_type.value,
            content=request.content,
            cleaned_content=cleaned,
            ocr_applied=ocr_applied,
            document=doc_meta,
            investment=investment,
            research=research,
            knowledge=knowledge,
            supersedes=supersedes if self.flags.kip_versioning else None,
            pipeline_stages=list(PIPELINE_STAGES),
        )
        if lineage_id:
            doc.lineage_id = lineage_id
        doc.document.version = version

        chunks = chunk_document(doc, dim=self.embedding_dim)
        stages.extend(["chunking", "embeddings", "hybrid_search_index"])

        self.store.put_document(doc, chunks)

        if self.flags.kip_versioning and supersedes:
            self.store.mark_superseded(supersedes, doc.document_id)

        if self.flags.kip_graph:
            upsert_from_document(doc, nodes=self.store.nodes, edges=self.store.edges)
            related_docs = [self.store.get_document(i) for i in related]
            related_docs = [d for d in related_docs if d is not None]
            link_related_research(doc, related_docs, edges=self.store.edges)
            stages.append("knowledge_graph")

        # Research timeline events
        if self.flags.kip_timeline:
            events: list[TimelineEvent] = []
            event_type = _event_type(doc.document.document_type, cleaned)
            for t in doc.investment.tickers:
                events.append(
                    TimelineEvent(
                        ticker=t,
                        event_date=doc.document.date or date.today(),
                        event_type=event_type,
                        title=doc.document.title,
                        document_id=doc.document_id,
                        source=doc.document.source,
                        summary=doc.knowledge.summary or doc.research.investment_thesis[:240],
                    )
                )
            for te in research.timeline_events:
                try:
                    ed = date.fromisoformat(str(te.get("date")))
                except Exception:
                    continue
                for t in doc.investment.tickers or ["UNKNOWN"]:
                    events.append(
                        TimelineEvent(
                            ticker=t,
                            event_date=ed,
                            event_type="mentioned_date",
                            title=str(te.get("context", ""))[:160],
                            document_id=doc.document_id,
                            source=doc.document.source,
                            summary=str(te.get("context", ""))[:240],
                        )
                    )
            self.store.add_timeline_events(events)

        if self.flags.kip_house_view and doc.investment.tickers:
            stages.append("house_view_update")

        stages.append("institutional_knowledge_base")
        doc.pipeline_stages = stages
        # refresh stored doc with final stages list
        self.store.documents[doc.document_id] = doc
        return doc


def _event_type(dtype: DocumentType, content: str) -> str:
    text = (content or "").lower()
    if "upgrade" in text:
        return "broker_upgrade"
    if "downgrade" in text:
        return "broker_downgrade"
    if dtype == DocumentType.EARNINGS_TRANSCRIPT or "earnings" in text:
        return "earnings"
    if dtype in {
        DocumentType.AGI_RESEARCH,
        DocumentType.AGI_NOTE,
        DocumentType.AGI_CIO_REPORT,
        DocumentType.AGI_INVESTMENT_OFFICE,
        DocumentType.AGI_MODEL_PORTFOLIO,
    }:
        return "agi_research"
    if dtype == DocumentType.AGI_DAILY_BRIEF:
        return "agi_daily_brief"
    if "interview" in text:
        return "management_interview"
    if dtype == DocumentType.CENTRAL_BANK_REPORT or "rbi" in text or "fed" in text:
        return "policy"
    if "broker" in dtype.value:
        return "broker_research"
    if "filing" in dtype.value:
        return "filing"
    return dtype.value
