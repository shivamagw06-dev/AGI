"""Editorial layer schema — soft presentation module, not an intelligence engine."""

from __future__ import annotations

PROGRAMME = "AGIB Editorial Intelligence Layer"
EDITORIAL_VERSION = "v1.2.0"
ARCHITECTURE_STATUS = "SOFT_WIRE"
ROLE = "writer_only"
NEVER_ANALYSES = True
NEVER_OVERRIDES_RECOMMENDATION = True
NEVER_INGESTS_DOCUMENTS = True

# Allowed keys in structured intelligence packages sent to editorial providers.
ALLOWED_STRUCTURED_KEYS = frozenset(
    {
        "recommendation",
        "conviction",
        "business_quality",
        "financial_quality",
        "valuation",
        "valuation_evidence",
        "framework_status",
        "top_reasons",
        "top_risks",
        "investment_horizon",
        "company",
        "ticker",
        "stance",
        "confidence",
        "evidence_insufficient",
        "investment_thesis_status",
        "not_a_negative_view",
        "mode",
        "question",
    }
)

# Forbidden payload shapes / keys — must never reach Gemini.
FORBIDDEN_KEYS = frozenset(
    {
        "pdf",
        "pdfs",
        "annual_report",
        "annual_reports",
        "news",
        "articles",
        "conference_call",
        "transcript",
        "transcripts",
        "financial_statements",
        "raw_financials",
        "document",
        "documents",
        "document_url",
        "content",
        "html",
        "filing_text",
        "full_text",
        "embeddings",
        "vector",
    }
)
