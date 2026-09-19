"""AGI V1.3 — Institutional Morning Office / Investment Office constants."""

from __future__ import annotations

IO_V13_WORKSTREAM_ID = "IO-V1.3"
IO_V13_PRODUCT = "Investment Office"
IO_V13_VERSION = "io-v1.3.1"
IO_V13_SPEC = "docs/AGI_IO_V131_PERFORMANCE_OPS.md"
IO_V13_PLATFORM = "AGI V1.3.1"

# Performance & Operations — data classes for the Morning Office hot path
DATA_CLASSES = {
    "morning_brief": {
        "freshness": "once_per_day_plus_manual_refresh",
        "delivery": "precomputed_snapshot",
    },
    "operational_metrics": {
        "freshness": "every_5_to_15_minutes",
        "delivery": "cached_aggregates",
    },
    "live_status": {
        "freshness": "seconds",
        "delivery": "live_api",
    },
}

MISSION = (
    "Institutional Morning Office — daily investment desk command center. "
    "Monitors overnight knowledge, research queue, macro, earnings, portfolio "
    "and analyst priorities. No BUY. No SELL."
)

ROLE = (
    "Morning command center for the research team. Complements Knowledge Operations "
    "without duplicating the knowledge pipeline control room."
)

POLICY = {
    "issues_recommendations": False,
    "buy_sell": False,
    "monitoring_only": True,
    "complements": "Knowledge Operations (KOC)",
}

SECTORS = (
    "IT",
    "Banking",
    "Auto",
    "Pharma",
    "Energy",
    "Infrastructure",
    "Capital Goods",
    "FMCG",
    "Real Estate",
    "Utilities",
)

RESEARCH_QUEUE_STAGES = (
    "Waiting Review",
    "Waiting Validation",
    "Waiting Publication",
    "Waiting Refresh",
    "Waiting Evidence",
    "Waiting Claim Safety",
)
