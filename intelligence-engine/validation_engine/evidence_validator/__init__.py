"""Evidence validator — can AGIB answer with available evidence?"""

from __future__ import annotations

from typing import Any


def validate_evidence(
    *,
    question: str,
    primary_objective: str | None = None,
    entity_status: dict[str, Any] | None = None,
    acquisition_planner: dict[str, Any] | None = None,
    evidence_inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q = (question or "").lower()
    obj = (primary_objective or "").lower()
    ent = entity_status or {}
    inv = evidence_inventory or {}
    acq = acquisition_planner or {}

    # Default institutional inventory assumptions (soft-wire)
    defaults = {
        "filings": True,
        "historical_financials": True,
        "peers": True,
        "macro": True,
        "forecast_inputs": True,
        "management_transcript": False,  # often pending
        "peer_history_pre_2015": False,
        "live_valuation_delay_minutes": 15,
        "consensus_provider_available": False,
    }
    defaults.update({k: v for k, v in inv.items() if v is not None})

    required: list[str] = []
    if any(x in obj for x in ("investment", "decision", "buy", "sell")) or "should i" in q:
        required = ["filings", "historical_financials", "peers", "macro"]
    elif "compare" in q or "comparison" in obj:
        required = ["peers", "historical_financials"]
    elif "explain" in q or "educational" in obj:
        required = []
    elif "macro" in obj or "rbi" in q:
        required = ["macro"]
    elif "portfolio" in q or "portfolio" in obj:
        required = ["peers", "macro"]
    elif "forecast" in obj or "forecast" in q:
        required = ["historical_financials", "forecast_inputs", "macro"]
    elif "risk" in obj or "risk" in q:
        required = ["filings", "macro"]
    elif "history" in q or "valuation" in obj:
        required = ["historical_financials", "peers"]
    else:
        required = ["filings"] if ent.get("canonical_entity") else []

    missing = [r for r in required if not defaults.get(r, False)]
    warnings: list[str] = []
    if not defaults.get("management_transcript", True) and required:
        warnings.append("Latest management transcript pending")
    if not defaults.get("peer_history_pre_2015", True) and "peers" in required:
        warnings.append("Peer history incomplete beyond 2015")
    delay = int(defaults.get("live_valuation_delay_minutes") or 0)
    if delay > 0 and ("buy" in q or "valuation" in obj or "overvalued" in q):
        warnings.append(f"Current valuation data delayed by {delay} minutes")
    if not defaults.get("consensus_provider_available", True) and ("forecast" in q or "should i" in q):
        warnings.append("Consensus estimates from one provider unavailable")

    # acquisition planner reuse/quality soft signal
    reuse = int((acq.get("metrics") or {}).get("reuse_count") or acq.get("reuse_count") or 0)
    api_reduction = float((acq.get("metrics") or {}).get("api_reduction") or 0)

    coverage = 1.0
    if required:
        coverage = (len(required) - len(missing)) / len(required)
    score = coverage
    if warnings:
        score -= 0.05 * min(len(warnings), 3)
    if reuse >= 2:
        score = min(1.0, score + 0.05)
    if api_reduction >= 0.3:
        score = min(1.0, score + 0.02)

    score = max(0.0, min(1.0, score))
    if missing:
        status = "insufficient" if coverage < 0.5 else "warning"
    elif warnings:
        status = "warning"
    else:
        status = "sufficient"

    return {
        "status": status,
        "score": round(score, 4),
        "required": required,
        "missing": missing,
        "warnings": warnings,
        "can_answer": coverage >= 0.5 and not (ent.get("needs_clarification") and not ent.get("canonical_entity")),
        "filings_exist": bool(defaults.get("filings")),
        "historical_data_exist": bool(defaults.get("historical_financials")),
        "peers_available": bool(defaults.get("peers")),
        "macro_available": bool(defaults.get("macro")),
        "forecast_possible": bool(defaults.get("forecast_inputs")),
    }
