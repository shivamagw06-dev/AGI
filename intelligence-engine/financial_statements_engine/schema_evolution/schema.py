"""FSE-04 Schema Evolution Engine — contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-04"
SUBSYSTEM = "schema_evolution"
VERSION = "schema-evolution-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "schema_evolution_only_no_buy_sell"

MAPPING_STATUSES = ("active", "deprecated")
REPORTING_STANDARDS = ("IND_AS", "IFRS", "US_GAAP", "OTHER", "UNKNOWN")
