"""Standard Phase 2 engine contract — mandatory envelope for every workstream."""

from __future__ import annotations

from typing import Any

# Required top-level keys on every Phase 2 engine response / package.
STANDARD_OUTPUT_KEYS = (
    "evidence",
    "confidence",
    "freshness",
    "lineage",
)

STANDARD_CONTRACT_KEYS = (
    "engine",
    "version",
    "inputs",
    "outputs",
    "consumers",
    "dependencies",
    "failure_mode",
    "baseline_compatible",
)

DEFAULT_CONSUMERS = ("decision_engine", "evaluation_lab")

DEFAULT_FAILURE_MODE = {
    "strategy": "degrade_gracefully",
    "block_unrelated_engines": False,
    "fabricated": False,
}

# Per-engine declared inputs / dependencies / SLA (days) for freshness scorecard.
ENGINE_CONTRACTS: dict[str, dict[str, Any]] = {
    "live_market_context": {
        "id": "P2.6",
        "engine_name": "Live Market Context",
        "inputs": ["company_pack", "live_data"],
        "dependencies": ["forecast_provider_integration", "groww", "yahoo_failover"],
        "score_field": "context_quality",
        "freshness_sla_days": 0,  # session / live
        "runtime_budget_s": 1.0,
    },
    "ownership_intelligence": {
        "id": "P2.3",
        "engine_name": "Ownership Intelligence",
        "inputs": ["company_pack", "live_data", "nse_shareholding_master", "nse_shp_xbrl"],
        "dependencies": ["institutional_data.shareholding", "live_data.nse_session"],
        "score_field": "ownership_quality",
        "freshness_sla_days": 45,
        "runtime_budget_s": 2.0,
    },
    "earnings_intelligence": {
        "id": "P2.1",
        "engine_name": "Financial Statements & Earnings Intelligence",
        "inputs": [
            "company_pack",
            "nse_integrated_filings",
            "nse_corporates_financial_results",
            "nse_indas_xbrl",
        ],
        "dependencies": ["institutional_data.financials", "live_data.nse_session"],
        "score_field": "forecast_confidence",
        "freshness_sla_days": 14,
        "runtime_budget_s": 2.5,
    },
    "valuation_intelligence": {
        "id": "P2.2",
        "engine_name": "Valuation Intelligence",
        "inputs": [
            "company_pack",
            "earnings_intelligence",
            "ownership_intelligence",
            "live_market_context",
            "valuation_peer_registry",
            "peer_intelligence",
        ],
        "dependencies": [
            "earnings_intelligence",
            "ownership_intelligence",
            "live_market_context",
            "peer_intelligence",
        ],
        "score_field": "valuation_confidence",
        "freshness_sla_days": 14,
        "runtime_budget_s": 3.0,
    },
    "sector_intelligence_playbooks": {
        "id": "P2.5",
        "engine_name": "Sector Intelligence",
        "inputs": ["company_pack", "knowledge_graph"],
        "dependencies": ["institutional_playbooks", "peer_intelligence", "continuous_sector_knowledge"],
        "score_field": "playbook_fit",
        "freshness_sla_days": 90,
        "runtime_budget_s": 0.5,
    },
    "catalyst_intelligence": {
        "id": "P2.4",
        "engine_name": "Catalyst Intelligence",
        "inputs": ["company_pack", "live_data", "knowledge_graph", "earnings_intelligence"],
        "dependencies": ["catalyst_trigger_intelligence", "forecast_intelligence"],
        "score_field": "catalyst_clarity",
        "freshness_sla_days": 7,
        "runtime_budget_s": 1.5,
    },
}


def build_engine_contract(engine_code: str, *, version: str | None = None) -> dict[str, Any]:
    """Return the standard contract declaration for a Phase 2 engine."""
    meta = ENGINE_CONTRACTS[engine_code]
    ver = version or f"{meta['id'].lower().replace('.', '')}-v1.0.0"
    return {
        "engine": engine_code,
        "engine_name": meta["engine_name"],
        "workstream_id": meta["id"],
        "version": ver,
        "inputs": list(meta["inputs"]),
        "outputs": {
            "score_field": meta["score_field"],
            "evidence": [],
            "confidence": None,
            "freshness": {
                "age_days": None,
                "stale": None,
                "sla_days": meta["freshness_sla_days"],
            },
            "lineage": [],
        },
        "consumers": list(DEFAULT_CONSUMERS),
        "dependencies": list(meta["dependencies"]),
        "failure_mode": dict(DEFAULT_FAILURE_MODE),
        "runtime_budget_s": meta["runtime_budget_s"],
        "baseline_compatible": True,
    }


def empty_engine_payload(engine_code: str, *, ticker: str, reason: str) -> dict[str, Any]:
    """Graceful degradation payload — never blocks unrelated engines."""
    contract = build_engine_contract(engine_code)
    return {
        "enabled": True,
        "ticker": ticker,
        "engine": engine_code,
        "version": contract["version"],
        "contract": contract,
        "score": None,
        "evidence": [],
        "confidence": 0.0,
        "freshness": {"age_days": None, "stale": True, "sla_days": contract["outputs"]["freshness"]["sla_days"]},
        "lineage": [],
        "degraded": True,
        "degraded_reason": reason,
        "failure_mode": dict(DEFAULT_FAILURE_MODE),
        "fabricated": False,
        "baseline_compatible": True,
    }


def validate_engine_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a Phase 2 engine response against the standard contract."""
    missing = [k for k in STANDARD_OUTPUT_KEYS if k not in payload]
    ok = (
        not missing
        and payload.get("fabricated") is not True
        and payload.get("baseline_compatible", True) is True
        and (payload.get("failure_mode") or {}).get("block_unrelated_engines") is not True
    )
    return {
        "ok": ok,
        "missing_output_keys": missing,
        "fabricated": payload.get("fabricated"),
        "blocks_unrelated": (payload.get("failure_mode") or {}).get("block_unrelated_engines"),
    }
