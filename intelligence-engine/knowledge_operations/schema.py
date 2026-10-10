"""KOC V1.2 — Institutional Knowledge Mission Control constants."""

from __future__ import annotations

KOC_WORKSTREAM_ID = "KOC-01"
KOC_PRODUCT = "Knowledge Operations Center"
KOC_VERSION = "koc-01-v1.2.0"
KOC_SPEC = "docs/AGI_KOC_01_KNOWLEDGE_OPERATIONS_CENTER.md"
KOC_PLATFORM = "AGI V1.2"

MISSION = (
    "Monitor, Validate, Learn and Improve Institutional Knowledge across the AGI Universe."
)

ROLE = (
    "Command center for the Institutional Knowledge Operating System — "
    "not a developer dashboard."
)

DOCUMENT_UPLOAD_TYPES = (
    "annual_report",
    "quarterly_results",
    "investor_presentation",
    "transcript",
    "shareholding",
    "corporate_action",
    "management_guidance",
    "segment_data",
    "credit_rating",
    "investor_day",
    "other",
)

UPLOAD_EXTENSIONS = (".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".zip")

UPLOAD_PIPELINE = (
    "Upload",
    "Virus Scan",
    "Checksum",
    "Version",
    "OCR",
    "Extract",
    "Parse",
    "Normalize",
    "Evidence Objects",
    "Claims",
    "Company Memory",
    "Knowledge Graph",
    "Research Ready",
    "Institutional Coverage",
    "Knowledge Snapshot",
    "Refresh Research",
)

MISSING_PRIORITY = {
    "financial_statements": "Critical",
    "annual_reports": "Critical",
    "quarterly_results": "Critical",
    "earnings_presentations": "Critical",
    "earnings_call_transcripts": "High",
    "shareholding": "High",
    "segment_kpis": "High",
    "corporate_actions": "Medium",
    "management_guidance": "Medium",
    "company_memory": "Medium",
    "knowledge_graph": "Low",
}

PRIORITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

# Weight used for Estimated ICC Gain (aligned with ICF evidence classes)
CLASS_WEIGHTS = {
    "annual_reports": 10,
    "quarterly_results": 10,
    "financial_statements": 20,
    "earnings_presentations": 10,
    "earnings_call_transcripts": 10,
    "shareholding": 10,
    "corporate_actions": 5,
    "management_guidance": 5,
    "segment_kpis": 10,
    "company_memory": 5,
    "knowledge_graph": 5,
}

CLASS_LABELS = {
    "annual_reports": "Annual Report",
    "quarterly_results": "Quarterly Results",
    "financial_statements": "Financial Statements",
    "earnings_presentations": "Investor Presentation",
    "earnings_call_transcripts": "Earnings Call Transcript",
    "shareholding": "Shareholding Pattern",
    "corporate_actions": "Corporate Action",
    "management_guidance": "Management Guidance",
    "segment_kpis": "Segment KPIs",
    "company_memory": "Company Memory",
    "knowledge_graph": "Knowledge Graph",
    "credit_rating": "Credit Rating",
    "investor_day": "Investor Day",
}

CHECKLIST_ORDER = (
    "financial_statements",
    "annual_reports",
    "quarterly_results",
    "earnings_presentations",
    "earnings_call_transcripts",
    "shareholding",
    "corporate_actions",
    "management_guidance",
    "investor_day",
    "credit_rating",
    "segment_kpis",
    "company_memory",
    "knowledge_graph",
    "evidence_registry",
    "research_pack",
)

QUEUE_STAGES = (
    "Waiting OCR",
    "Waiting Parsing",
    "Waiting Validation",
    "Waiting Embedding",
    "Waiting Company Memory",
    "Waiting Knowledge Graph",
    "Waiting Research Refresh",
    "Retry Queue",
    "Repair Queue",
)

COLLECTOR_NAMES = (
    "Annual Reports",
    "Quarterly Results",
    "Investor Presentations",
    "Transcripts",
    "Shareholding",
    "Corporate Actions",
    "NSE",
    "BSE",
    "Yahoo",
    "Groww",
    "Company IR",
    "FRED",
    "RBI",
    "World Bank",
)

GLOBAL_SEARCH_SCOPES = (
    "companies",
    "evidence",
    "documents",
    "claims",
    "knowledge_versions",
    "research_packs",
)
