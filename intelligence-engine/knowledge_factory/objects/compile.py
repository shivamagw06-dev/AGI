"""Company / Sector / Macro Knowledge Object compilers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

OBJECT_VERSION = "kf-objects-v1.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compile_company(
    *,
    entity: str,
    profile: dict[str, Any],
    valuation: dict[str, Any],
    accounting: dict[str, Any],
    business_quality: dict[str, Any],
    risk: dict[str, Any],
    peers: dict[str, Any],
    timeline: dict[str, Any],
    evidence_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    e = entity.upper()
    missing = []
    if valuation.get("insufficient"):
        missing.extend(valuation.get("insufficient") or ["valuation"])
    if risk.get("insufficient"):
        missing.append("risk")
    if peers.get("insufficient"):
        missing.append("peers")
    coverage = round(max(0.0, 1.0 - 0.12 * len(missing)), 4)
    quality = 88.0 if coverage >= 0.7 else 55.0
    return {
        "object_version": OBJECT_VERSION,
        "kind": "company_knowledge_object",
        "entity": e,
        "company_profile": {
            "entity": e,
            "sector": profile.get("sector"),
            "market_cap": profile.get("market_cap"),
        },
        "historical_financials": profile.get("primitives") or {},
        "historical_valuation": valuation,
        "accounting": accounting,
        "business_quality": business_quality,
        "management": {"events": [x for x in (timeline.get("events") or []) if "CEO" in str(x.get("title") or "").upper()]},
        "risk": risk,
        "macro_sensitivity": {"beta": risk.get("beta"), "sector": profile.get("sector")},
        "sector": profile.get("sector"),
        "peer_group": peers,
        "timeline": timeline,
        "corporate_actions": [x for x in (timeline.get("events") or []) if x.get("type") in {"dividend", "buyback", "capital_raise"}],
        "evidence_packs": evidence_pack or {},
        "quality_score": quality,
        "coverage": coverage,
        "missing_fields": missing,
        "last_updated": _now(),
        "provider": "knowledge_factory",
    }


def compile_sector(sector_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_version": OBJECT_VERSION,
        "kind": "sector_knowledge_object",
        **sector_payload,
        "last_updated": _now(),
    }


def compile_macro(macro_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_version": OBJECT_VERSION,
        "kind": "macro_knowledge_object",
        **macro_payload,
        "last_updated": _now(),
    }
