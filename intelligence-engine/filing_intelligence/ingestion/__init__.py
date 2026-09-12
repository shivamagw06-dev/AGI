from filing_intelligence.ingestion.detect import detect_doc_type
from filing_intelligence.ingestion.store import (
    all_documents,
    documents_for,
    get_document,
    ingest_document,
    reset_for_tests,
)

__all__ = [
    "all_documents",
    "detect_doc_type",
    "documents_for",
    "get_document",
    "ingest_document",
    "reset_for_tests",
]
