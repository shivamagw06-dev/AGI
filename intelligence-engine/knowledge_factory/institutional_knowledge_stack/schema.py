"""Institutional Knowledge Stack schema — soft orchestration only."""

from __future__ import annotations

from typing import Any

STACK_VERSION = "institutional-knowledge-stack-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Knowledge Stack"
LAYER = "IKS"
ARCHITECTURE_STATUS = "SOFT_KNOWLEDGE_STACK_INTEGRATION"

# Ordered reality → expectations stack
STACK_LAYERS: tuple[dict[str, str], ...] = (
    {"id": "universe", "name": "Universe Intelligence", "api": "/v1/universe-intelligence"},
    {"id": "company", "name": "Company Intelligence (ICI)", "api": "/v1/company-intelligence"},
    {"id": "corporate_events", "name": "Corporate Event Intelligence (ICEI)", "api": "/v1/corporate-events"},
    {"id": "government", "name": "Government Intelligence (IGRI)", "api": "/v1/government"},
    {"id": "industry", "name": "Industry & Value Chain (IIVI)", "api": "/v1/industry"},
    {"id": "relationships", "name": "Economic Relationships (IERI)", "api": "/v1/relationship"},
    {"id": "alternative_data", "name": "Alternative Data (IADI)", "api": "/v1/alternative-data"},
    {"id": "expectations", "name": "Market Expectations (IMEI)", "api": "/v1/expectations"},
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "governance": True,
    "committee_system": True,
    "planner": True,
    "learning_engine": True,
    "soft_wire_only": True,
    "not_a_reasoning_engine": True,
}
