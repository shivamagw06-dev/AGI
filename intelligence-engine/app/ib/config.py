"""IB configuration — event types, categories, defaults."""

from __future__ import annotations

EVENT_CATEGORIES = (
    "knowledge",
    "company",
    "sector",
    "theme",
    "forecast",
    "evidence",
    "investment_intelligence",
    "market_event",
    "portfolio",
    "risk",
    "monitoring",
    "notification",
    "system",
    "scheduler",
    "administration",
    "acquisition",
)

# Canonical v1 event types → category
EVENT_TYPES: dict[str, str] = {
    # Knowledge
    "KnowledgeCreated": "knowledge",
    "KnowledgeUpdated": "knowledge",
    "KnowledgeDeleted": "knowledge",
    # Evidence
    "EvidenceVerified": "evidence",
    "EvidenceRejected": "evidence",
    "EvidenceConflictDetected": "evidence",
    "ConfidenceChanged": "evidence",
    # Investment Intelligence
    "InvestmentThesisUpdated": "investment_intelligence",
    "RiskProfileChanged": "investment_intelligence",
    "CatalystDetected": "investment_intelligence",
    "ScenarioChanged": "investment_intelligence",
    "CompanyDNAUpdated": "investment_intelligence",
    # Forecasting
    "ForecastCreated": "forecast",
    "ForecastUpdated": "forecast",
    "ForecastResolved": "forecast",
    "ForecastCalibrationChanged": "forecast",
    "ForecastLearningGenerated": "forecast",
    # Market Events
    "CorporateEventDetected": "market_event",
    "MacroEventDetected": "market_event",
    "SectorEventDetected": "market_event",
    "ThemeEventDetected": "market_event",
    "ImpactPropagationCompleted": "market_event",
    # Acquisition
    "DocumentDiscovered": "acquisition",
    "DocumentDownloaded": "acquisition",
    "DocumentParsed": "acquisition",
    "KnowledgePublished": "acquisition",
    "CompanyUpdated": "company",
    # System
    "HealthChanged": "system",
    "ConnectorFailed": "system",
    "RetryScheduled": "system",
    "CacheInvalidated": "system",
}

PUBLISHERS = ("aoi", "eve", "iie", "fle", "mee", "cae", "system", "admin", "ask_agi")
FUTURE_SUBSCRIBERS = ("pmo", "ime", "rme", "ems", "ams", "notifications", "research_workspace")

# Events that should soft-invalidate CAE / related caches
CACHE_INVALIDATION_EVENTS = frozenset(
    {
        "InvestmentThesisUpdated",
        "ForecastUpdated",
        "ForecastResolved",
        "CorporateEventDetected",
        "EvidenceVerified",
        "KnowledgeUpdated",
        "CompanyUpdated",
        "ImpactPropagationCompleted",
        "CacheInvalidated",
    }
)

DEFAULT_RETRY_MAX = 3
DEFAULT_BACKOFF_MS = (10, 50, 150)
DEFAULT_RETENTION_EVENTS = 5000
DEFAULT_HANDLER_TIMEOUT_MS = 2000
SCHEMA_VERSION = "ib-event-v1"
