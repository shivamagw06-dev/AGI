"""KG-01 — Institutional Knowledge Graph constants (single-company scope)."""

from __future__ import annotations

KG_WORKSTREAM_ID = "KG-01"
KG_PRODUCT = "Institutional Knowledge Graph"
KG_VERSION = "kg-01-v1.0.0"
KG_SPEC = "docs/AGI_KG_01_INSTITUTIONAL_KNOWLEDGE_GRAPH.md"
KG_ROLE = "deterministic_company_knowledge_graph"
GRAPH_ENGINE_VERSION = "kg-01-graph-engine-v1"
INFERENCE_VERSION = "kg-01-inference-v1"
TRAVERSAL_VERSION = "kg-01-traversal-v1"
IMPACT_VERSION = "kg-01-impact-v1"

ENTITY_TYPES = (
    "Company",
    "Sector",
    "Industry",
    "Country",
    "Management",
    "FinancialMetric",
    "MacroVariable",
    "ValuationMetric",
    "Risk",
    "Catalyst",
    "Forecast",
    "Reason",
    "Decision",
    "Evidence",
    "Calibration",
    "Portfolio",
    "Watchlist",
)

RELATIONSHIP_KINDS = (
    "positive",
    "negative",
    "supports",
    "pressures",
    "derived",
    "evidences",
    "impacts",
    "belongs_to",
    "monitors",
)
