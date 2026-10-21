"""LIDI Track 2 — production verification & certification schemas."""

from __future__ import annotations

from typing import Any

VERIFY_VERSION = "live-collector-activation-v1.0.0"
PROGRAMME = "AGIB v3.0 – Live Collector Activation & Production Verification"
MODULE_CODE = "LIDI-T2"

CERTIFICATION_LEVELS = (
    "NOT_IMPLEMENTED",
    "DEVELOPMENT",
    "TESTING",
    "STAGING",
    "PRODUCTION_READY",
    "CERTIFIED",
)

# CERTIFIED requires N consecutive successful *live* daily runs (no fixture, no recorded sample).
CERTIFIED_CONSECUTIVE_LIVE_RUNS = 7

DATA_MODES = ("LIVE", "SEED", "FIXTURE", "SNAPSHOT", "INJECTED", "RECORDED_SAMPLE", "UNKNOWN")

FREEZE_LOCKS: dict[str, Any] = {
    "reasoning": True,
    "knowledge_factory": True,
    "ask_pipeline": True,
    "institutional_scheduler": True,
    "research_office": True,
    "lidi_track1_architecture": True,
    "soft_wire_only": True,
    "never_silent_fixture_fallback": True,
    "never_raw_to_reasoning": True,
}

COLLECTOR_SPECS: tuple[dict[str, Any], ...] = (
    {
        "source_id": "nse_bhavcopy",
        "collector_id": "lidi_nse_bhavcopy_v1",
        "name": "NSE Bhavcopy",
        "official_source": "NSE India",
        "verify": [
            "daily_download",
            "price_history",
            "volume",
            "corporate_adjustments",
            "historical_continuity",
            "replay",
        ],
    },
    {
        "source_id": "nse_announcements",
        "collector_id": "lidi_nse_announcements_v1",
        "name": "NSE Corporate Announcements",
        "official_source": "NSE India",
        "verify": [
            "announcements",
            "results",
            "board_meetings",
            "guidance",
            "corporate_disclosures",
            "timeline_updates",
        ],
    },
    {
        "source_id": "bse_corporate_actions",
        "collector_id": "lidi_bse_corporate_actions_v1",
        "name": "BSE Corporate Actions",
        "official_source": "BSE India",
        "verify": [
            "dividend",
            "split",
            "bonus",
            "rights",
            "buyback",
            "merger",
            "historical_replay",
        ],
    },
    {
        "source_id": "rbi_dbie",
        "collector_id": "lidi_rbi_dbie_v1",
        "name": "RBI DBIE",
        "official_source": "Reserve Bank of India DBIE",
        "verify": [
            "rates",
            "credit",
            "deposits",
            "liquidity",
            "macro_series",
            "historical_revisions",
        ],
    },
    {
        "source_id": "company_ir",
        "collector_id": "lidi_company_ir_v1",
        "name": "Company Investor Relations",
        "official_source": "Company IR websites",
        "verify": [
            "quarterly_results",
            "annual_reports",
            "investor_presentations",
            "guidance",
            "press_releases",
        ],
    },
)

PRODUCTION_CHECKLIST = (
    "live_endpoint_reachable",
    "authentication",
    "successful_download",
    "schema_validation",
    "duplicate_detection",
    "historical_consistency",
    "checksum_validation",
    "provenance_complete",
    "point_in_time_fields",
    "derived_producers_executed",
    "knowledge_objects_updated",
    "evidence_packs_regenerated",
    "scheduler_integration",
    "research_office_updated",
    "ask_pipeline_reads_live_objects",
    "replay_deterministic",
)
