"""IDI — Institutional Documents Intelligence schemas."""

from __future__ import annotations

from typing import Any

IDI_VERSION = "institutional-documents-intelligence-v1.0.0"
PROGRAMME = "AGIB v3.1 – Institutional Documents Intelligence"
LAYER = "IDI"
MODULE_CODE = "IDI"

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "knowledge_factory_core": True,
    "universe_intelligence": True,
    "historical_intelligence": True,
    "company_intelligence": True,
    "corporate_events": True,
    "government_intelligence": True,
    "industry_intelligence": True,
    "economic_relationship_intelligence": True,
    "alternative_data_intelligence": True,
    "market_expectations_intelligence": True,
    "ask_pipeline": True,
    "institutional_scheduler": True,
    "research_office": True,
    "live_data_ingestion": True,
    "soft_wire_only": True,
    "no_reasoning": True,
    "no_summarisation": True,
    "no_recommendations": True,
    "never_document_to_reasoning": True,
}

DOCUMENT_TYPES: tuple[str, ...] = (
    "ANNUAL_REPORT",
    "QUARTERLY_REPORT",
    "INVESTOR_PRESENTATION",
    "CONFERENCE_CALL_TRANSCRIPT",
    "EXCHANGE_FILING",
    "CORPORATE_GOVERNANCE_REPORT",
    "ESG_REPORT",
    "CREDIT_RATING_REPORT",
    "PROSPECTUS",
    "OFFER_DOCUMENT",
    "SHAREHOLDER_NOTICE",
    "POSTAL_BALLOT",
    "VOTING_RESULTS",
    "CORPORATE_POLICY",
    "MANAGEMENT_COMMENTARY",
    "RISK_DISCLOSURE",
    "SEGMENT_REPORT",
    "NOTES_TO_ACCOUNTS",
)

OBJECT_TYPES: tuple[str, ...] = (
    "AnnualReportObject",
    "QuarterlyReportObject",
    "PresentationObject",
    "TranscriptObject",
    "GovernanceObject",
    "RiskDisclosureObject",
    "AccountingNoteObject",
    "SegmentObject",
)

DOC_TYPE_TO_OBJECT: dict[str, str] = {
    "ANNUAL_REPORT": "AnnualReportObject",
    "QUARTERLY_REPORT": "QuarterlyReportObject",
    "INVESTOR_PRESENTATION": "PresentationObject",
    "CONFERENCE_CALL_TRANSCRIPT": "TranscriptObject",
    "CORPORATE_GOVERNANCE_REPORT": "GovernanceObject",
    "RISK_DISCLOSURE": "RiskDisclosureObject",
    "NOTES_TO_ACCOUNTS": "AccountingNoteObject",
    "SEGMENT_REPORT": "SegmentObject",
    "EXCHANGE_FILING": "GovernanceObject",
    "ESG_REPORT": "GovernanceObject",
    "MANAGEMENT_COMMENTARY": "AnnualReportObject",
    "CREDIT_RATING_REPORT": "RiskDisclosureObject",
    "PROSPECTUS": "GovernanceObject",
    "OFFER_DOCUMENT": "GovernanceObject",
    "SHAREHOLDER_NOTICE": "GovernanceObject",
    "POSTAL_BALLOT": "GovernanceObject",
    "VOTING_RESULTS": "GovernanceObject",
    "CORPORATE_POLICY": "GovernanceObject",
}

EVIDENCE_PACK_KINDS: tuple[str, ...] = (
    "DOCUMENT_PACK",
    "MANAGEMENT_PACK",
    "ACCOUNTING_PACK",
    "RISK_PACK",
    "GOVERNANCE_PACK",
    "SEGMENT_PACK",
    "TRANSCRIPT_PACK",
)

OFFICIAL_SOURCES: tuple[str, ...] = (
    "COMPANY_IR",
    "NSE_FILINGS",
    "BSE_FILINGS",
    "SEBI",
    "MCA",
    "COMPANY_WEBSITE",
    "RATING_AGENCY_PUBLIC",
)

PARSER_SECTIONS: tuple[str, ...] = (
    "MANAGEMENT_DISCUSSION",
    "FINANCIAL_STATEMENTS",
    "NOTES",
    "RISK_FACTORS",
    "CAPITAL_ALLOCATION",
    "BUSINESS_SEGMENTS",
    "GUIDANCE",
    "STRATEGY",
    "TABLES",
    "OTHER",
)
