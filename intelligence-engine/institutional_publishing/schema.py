"""PUB-01 — Publishing & Distribution constants."""

from __future__ import annotations

PUB_WORKSTREAM_ID = "PUB-01"
PUB_PRODUCT = "Publishing & Distribution"
PUB_VERSION = "pub-01-v1.0.0"
PUB_SPEC = "docs/AGI_PUB_01_PUBLISHING.md"
PUB_ROLE = "compose_only_no_analysis"
PUBLICATION_ENGINE_VERSION = "pub-01-engine-v1"
DEFAULT_TEMPLATE_VERSION = "1.0.0"

# PUB never analyzes — it composes immutable institutional objects
ANALYZES = False
GENERATES_RECOMMENDATIONS = False
REINTERPRETS_EVIDENCE = False

PUBLICATION_TYPES = (
    # Market
    "MorningBrief",
    "EveningBrief",
    "MarketWrap",
    "MacroUpdate",
    # Company
    "CompanyResearchNote",
    "InvestmentSnapshot",
    "DecisionUpdate",
    "ObservationBulletin",
    # Portfolio
    "PortfolioReview",
    "RiskSummary",
    "PolicyReview",
    "AllocationChanges",
    # Committee
    "InvestmentCommitteePack",
    "MeetingAgenda",
    "ResolutionSummary",
    "ActionRegister",
    # Client
    "WeeklyClientReport",
    "MonthlyReview",
    "QuarterlyLetter",
    "MandateReport",
)

PUBLICATION_CATEGORIES = (
    "market",
    "company",
    "portfolio",
    "committee",
    "client",
)

TYPE_TO_CATEGORY = {
    "MorningBrief": "market",
    "EveningBrief": "market",
    "MarketWrap": "market",
    "MacroUpdate": "market",
    "CompanyResearchNote": "company",
    "InvestmentSnapshot": "company",
    "DecisionUpdate": "company",
    "ObservationBulletin": "company",
    "PortfolioReview": "portfolio",
    "RiskSummary": "portfolio",
    "PolicyReview": "portfolio",
    "AllocationChanges": "portfolio",
    "InvestmentCommitteePack": "committee",
    "MeetingAgenda": "committee",
    "ResolutionSummary": "committee",
    "ActionRegister": "committee",
    "WeeklyClientReport": "client",
    "MonthlyReview": "client",
    "QuarterlyLetter": "client",
    "MandateReport": "client",
}

RENDERERS = ("html", "pdf", "markdown", "json")
DISTRIBUTION_TARGETS = ("workspace", "email", "api", "export", "archive")

# Required source object types per publication (composition plan — not analysis)
REQUIRED_SOURCES: dict[str, tuple[str, ...]] = {
    "MorningBrief": ("Observation", "PortfolioRisk", "Macro"),
    "EveningBrief": ("Observation", "PortfolioRisk"),
    "MarketWrap": ("Observation", "Macro"),
    "MacroUpdate": ("Macro", "Observation"),
    "CompanyResearchNote": ("CompanyDecision", "Evidence", "Observation"),
    "InvestmentSnapshot": ("CompanyDecision", "Evidence"),
    "DecisionUpdate": ("CompanyDecision", "Observation"),
    "ObservationBulletin": ("Observation", "Evidence"),
    "PortfolioReview": ("PortfolioDecision", "PortfolioRisk", "PolicyAssessment"),
    "RiskSummary": ("PortfolioRisk",),
    "PolicyReview": ("PolicyAssessment",),
    "AllocationChanges": ("PortfolioDecision", "PortfolioRisk"),
    "InvestmentCommitteePack": ("CommitteeResolution", "PortfolioDecision", "PortfolioRisk", "PolicyAssessment"),
    "MeetingAgenda": ("CommitteeResolution", "PortfolioDecision"),
    "ResolutionSummary": ("CommitteeResolution",),
    "ActionRegister": ("CommitteeResolution",),
    "WeeklyClientReport": ("PortfolioDecision", "PortfolioRisk", "Observation"),
    "MonthlyReview": ("PortfolioDecision", "PortfolioRisk", "PolicyAssessment", "CommitteeResolution"),
    "QuarterlyLetter": ("PortfolioDecision", "CommitteeResolution", "Macro"),
    "MandateReport": ("PolicyAssessment", "PortfolioRisk"),
}

LINEAGE_VIEW = (
    "Observation",
    "Decision",
    "Risk",
    "Committee",
    "Evidence",
)
