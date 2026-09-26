"""P2.6 Live Market Context — schema & version."""

from __future__ import annotations

ENGINE_CODE = "live_market_context"
ENGINE_NAME = "Live Market Context"
VERSION = "p2.6-v1.0.0"
WORKSTREAM_ID = "P2.6"
MILESTONE = "phase_2_1"
PROGRAMME = "AGIB_LIVE_MARKET_CONTEXT"

# Price freshness SLA: session / live (0 days)
FRESHNESS_SLA_SEC = 300  # 5 minutes institutional soft SLA
RUNTIME_BUDGET_S = 1.0

# Never invent prices for unknown names.
FAIL_CLOSED_ON_MISSING_QUOTE = True
