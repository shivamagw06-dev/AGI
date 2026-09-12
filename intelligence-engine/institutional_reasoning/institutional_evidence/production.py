"""Phase 2 Institutional Evidence — production facade.

Soft-wire entry points for Ask AGI / governance. No new top-level engine.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.pack import (
    PACK_VERSION,
    build_institutional_pack,
)
from institutional_reasoning.institutional_evidence.quality import (
    MIN_FRAMEWORK_SCORE,
    QUALITY_VERSION,
)

MODULE_CODE = "IEI"
PROGRAMME = "Institutional Evidence Intelligence"
VERSION = "institutional-evidence-v1.0.0"


def build_evidence_pack(
    entity_id: str,
    *,
    entity_name: str | None = None,
    entity_type: str | None = None,
    existing_packs: dict[str, dict[str, Any]] | None = None,
    dcf_inputs: dict[str, Any] | None = None,
    financials: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_institutional_pack(
        entity_id,
        entity_name=entity_name,
        entity_type=entity_type,
        existing_packs=existing_packs,
        dcf_inputs=dcf_inputs,
        financials=financials,
    )


def package_for_governance(
    entity_id: str | None,
    *,
    entity_name: str | None = None,
    entity_type: str | None = None,
    existing_packs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compact pack for execution governance consumption."""
    if not entity_id:
        return {"found": False, "reason": "no_entity"}
    pack = build_evidence_pack(
        entity_id,
        entity_name=entity_name,
        entity_type=entity_type,
        existing_packs=existing_packs,
    )
    return {
        "found": True,
        "pack_version": PACK_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": VERSION,
        "institutional_evidence": pack,
        # Also expose validated DVC-shaped fields at top for alias walk
        "validated": pack.get("validated") or {},
        "symbol": pack.get("entity_id"),
        "entity_id": pack.get("entity_id"),
        "as_of": pack.get("as_of"),
        "current_pe": pack.get("current_pe"),
        "historical_pe": pack.get("historical_pe"),
        "historical_percentile": pack.get("historical_percentile"),
        "peer_pe": pack.get("peer_pe"),
        "peer_median_pe": pack.get("peer_median_pe"),
        "sector_pe": pack.get("sector_pe"),
        "roic": pack.get("roic"),
        "operating_margin": pack.get("operating_margin"),
        "cash_conversion": (pack.get("validated") or {}).get("cash_conversion", {}).get("value")
        if isinstance((pack.get("validated") or {}).get("cash_conversion"), dict)
        else None,
        "leverage": (pack.get("validated") or {}).get("leverage", {}).get("value")
        if isinstance((pack.get("validated") or {}).get("leverage"), dict)
        else None,
        "earnings_quality": (pack.get("validated") or {}).get("earnings_quality", {}).get("value")
        if isinstance((pack.get("validated") or {}).get("earnings_quality"), dict)
        else None,
        "peers": (pack.get("validated") or {}).get("peers", {}).get("value")
        if isinstance((pack.get("validated") or {}).get("peers"), dict)
        else None,
        "risk_drivers": pack.get("risk_drivers")
        or (
            (pack.get("validated") or {}).get("risk_drivers", {}).get("value")
            if isinstance((pack.get("validated") or {}).get("risk_drivers"), dict)
            else None
        ),
        "downside_case": pack.get("downside_case")
        if pack.get("downside_case") is not None
        else (
            (pack.get("validated") or {}).get("downside_case", {}).get("value")
            if isinstance((pack.get("validated") or {}).get("downside_case"), dict)
            else None
        ),
        "evidence_score": pack.get("evidence_score"),
        "coverage": pack.get("coverage"),
        "summary": pack.get("summary"),
        "modules": pack.get("modules"),
        "insufficient_fields": pack.get("insufficient_fields"),
    }


def quality_gates(tickers: list[str] | None = None) -> dict[str, Any]:
    sample = tickers or ["INFY", "NIFTYIT", "TCS"]
    rows = []
    for t in sample:
        pkg = package_for_governance(t)
        pack = pkg.get("institutional_evidence") or {}
        rows.append(
            {
                "ticker": t,
                "evidence_score": pack.get("evidence_score"),
                "coverage": pack.get("coverage"),
                "accepted": pack.get("accepted_for_frameworks"),
                "insufficient": pack.get("insufficient_fields"),
            }
        )
    return {
        "module": MODULE_CODE,
        "version": VERSION,
        "quality_version": QUALITY_VERSION,
        "min_framework_score": MIN_FRAMEWORK_SCORE,
        "rows": rows,
        "pass": all(r.get("accepted") for r in rows),
    }
