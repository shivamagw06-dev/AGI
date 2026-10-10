"""P2.3 Ownership Intelligence — schema & version."""

from __future__ import annotations

ENGINE_CODE = "ownership_intelligence"
ENGINE_NAME = "Ownership Intelligence"
VERSION = "p2.3-v1.0.0"
WORKSTREAM_ID = "P2.3"
MILESTONE = "phase_2_1"
PROGRAMME = "AGIB_OWNERSHIP_INTELLIGENCE"

# Shareholding filings are quarterly — institutional soft SLA
FRESHNESS_SLA_DAYS = 45
RUNTIME_BUDGET_S = 2.0
MIN_HISTORY_QUARTERS = 20

# Category keys in Ownership Pack v2
OWNERSHIP_FIELDS = (
    "promoter",
    "promoter_group",
    "public",
    "fii",
    "dii",
    "mutual_funds",
    "insurance",
    "banks",
    "pension",
    "aif",
    "government",
    "corporate_bodies",
    "retail",
    "others",
    "employee_trusts",
)

IC10_UNIVERSE = (
    "HDFCBANK",
    "RELIANCE",
    "TCS",
    "ETERNAL",
    "TMPV",
    "SUNPHARMA",
    "NTPC",
    "HAL",
    "ASIANPAINT",
    "ULTRACEMCO",
)
