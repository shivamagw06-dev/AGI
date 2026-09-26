"""AGI v4.0 Phase 5 Sprint 5.3 — Institutional Portfolio Office (IPO)."""

from __future__ import annotations

from typing import Any

IPO_VERSION = "institutional-portfolio-office-v1.0.0"
IDEA_SCHEMA_VERSION = "ipo-idea-schema-v1.0.0"
PROGRAMME = (
    "AGI v4.0 – Phase 5 Institutional Investment Office · Sprint 5.3 "
    "Institutional Portfolio Office"
)
MODULE_CODE = "IPO"
COMPANY = "AGI"
PRODUCT_LINE = "Institutional Investment Office"
OWNER = "AGI Investment Office"

FREEZE_LOCKS: dict[str, Any] = {
    "judgment_stack_v36": True,
    "investment_thesis": True,
    "decision_office": True,
    "no_positions": True,
    "no_orders": True,
    "no_execution": True,
    "no_brokerage": True,
    "relative_not_absolute": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_portfolio_inflation": True,
}

# Portfolio roles — not buy/sell
PORTFOLIO_ROLES: tuple[str, ...] = (
    "Core Compounder",
    "Defensive",
    "Cyclical",
    "Turnaround",
    "Event Driven",
    "Income",
    "Macro Hedge",
    "Cash Alternative",
    "Satellite",
)

IDEA_STATUSES: tuple[str, ...] = (
    "Candidate",
    "Active Consideration",
    "Parked",
    "Rejected",
    "Superseded",
)

# Governance constraints (policies) — not positions
DEFAULT_POLICIES: dict[str, Any] = {
    "max_single_name_ideas": 1,  # soft: count of Active Consideration per ticker in theme
    "max_sector_share_pct": 35.0,
    "max_theme_ideas": 12,
    "min_liquidity_tier": "standard",
    "allow_execution": False,
    "allow_positions": False,
}

# Illustrative peer universes for relative ranking (not holdings)
PEER_UNIVERSES: dict[str, tuple[str, ...]] = {
    "IT Services": ("TCS", "INFY", "LTIM", "PERSISTENT", "WIPRO", "HCLTECH"),
    "Private Banks": ("HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK"),
    "Energy": ("RELIANCE", "ONGC", "BPCL"),
    "Diversified": (),
}
