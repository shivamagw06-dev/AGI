"""PKG-01 / Phase 4.1 PO-01 — Portfolio Knowledge Graph constants."""

from __future__ import annotations

# Engine id PKG-01 avoids collision with portfolio_office state service (also historically PO-01).
PKG_WORKSTREAM_ID = "PKG-01"
PKG_SPRINT = "PO-01"  # Phase 4.1 programme sprint name
PKG_PRODUCT = "Portfolio Knowledge Graph"
PKG_VERSION = "pkg-01-v1.0.0"
PKG_SPEC = "docs/AGI_PKG_01_PORTFOLIO_KNOWLEDGE_GRAPH.md"
PKG_ROLE = "deterministic_portfolio_knowledge_graph"
PORTFOLIO_GRAPH_ENGINE_VERSION = "pkg-01-graph-engine-v1"
DEFAULT_PORTFOLIO_ID = "agi-core-equity"

ENTITY_TYPES = (
    "Portfolio",
    "Company",
    "Holding",
    "Allocation",
    "Sector",
    "Industry",
    "Country",
    "Decision",
    "Risk",
    "Exposure",
    "Correlation",
    "Cash",
)

RELATIONSHIP_KINDS = (
    "holds",
    "allocates",
    "belongs_to",
    "exposes",
    "correlates_with",
    "concentrates",
    "decides",
    "supports",
    "pressures",
)

LINEAGE_CHAIN = (
    "Holdings",
    "Company Graphs",
    "Portfolio Graph",
    "Allocations",
    "Exposures",
    "Concentration",
    "Correlations",
    "Portfolio Decisions",
)
