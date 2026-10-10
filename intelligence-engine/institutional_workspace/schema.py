"""RW-01 — Institutional Research Workspace constants."""

from __future__ import annotations

RW_WORKSTREAM_ID = "RW-01"
RW_PRODUCT = "Institutional Research Workspace"
RW_VERSION = "rw-01-v1.0.0"
RW_SPEC = "docs/AGI_RW_01_RESEARCH_WORKSPACE.md"
RW_ROLE = "analyst_workstation_presentation"
WORKSPACE_ENGINE_VERSION = "rw-01-workspace-v1"

WORKSPACE_CONTEXTS = (
    "company",
    "portfolio",
    "committee",
    "research",
    "market",
    "macro",
)

COMPANY_SECTIONS = (
    "overview",
    "investment_thesis",
    "business",
    "financials",
    "valuation",
    "risk",
    "forecast",
    "observations",
    "decision_history",
    "evidence",
    "knowledge_graph",
    "timeline",
    "related_companies",
    "research_notes",
)

PORTFOLIO_SECTIONS = (
    "overview",
    "holdings",
    "risk",
    "policy",
    "decision",
    "committee",
    "allocation_history",
    "observation_feed",
    "scenario_analysis",
)

NAVIGATION = (
    "Overview",
    "Timeline",
    "Evidence",
    "Decisions",
    "Risk",
    "Policy",
    "Committee",
    "Forecast",
    "Knowledge Graph",
    "Relationship Map",
    "Publications",
    "Notes",
    "Ask AGI",
)

LINEAGE_CHAIN = (
    "Evidence",
    "Reason",
    "Company Decision",
    "Portfolio Risk",
    "Policy Assessment",
    "Portfolio Decision",
    "Committee Resolution",
)
