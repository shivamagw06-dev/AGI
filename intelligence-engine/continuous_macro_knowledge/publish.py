"""Publish MKOs into the Macro Knowledge Store (no user interaction)."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.schema import MacroKnowledgeObject, utc_now
from continuous_macro_knowledge.store import STORE


def publish_mko(mko: MacroKnowledgeObject) -> dict[str, Any]:
    """Always publish validated knowledge objects; learning is separate."""
    mko.published = True
    mko.published_at = utc_now()
    frozen = STORE.put(mko)
    STORE.record_publication(
        {
            "mko_id": frozen.mko_id,
            "indicator": frozen.indicator,
            "country": frozen.country,
            "category": frozen.category,
            "version": frozen.version,
            "materiality_tier": frozen.materiality_tier,
            "learning_generated": frozen.learning_generated,
        }
    )
    # Soft bridge into KF macro store when available
    soft = _soft_kf_bridge(frozen)
    return {
        "published": True,
        "mko_id": frozen.mko_id,
        "version": frozen.version,
        "indicator": frozen.indicator,
        "country": frozen.country,
        "soft_kf": soft,
        "user_triggered": False,
    }


def _soft_kf_bridge(mko: MacroKnowledgeObject) -> dict[str, Any]:
    """Soft signal only — CMKP store is authoritative for Sprint 10.1."""
    return {
        "ok": True,
        "target": "macro_knowledge_store",
        "macro_id": f"CMKP:{mko.country}:{mko.indicator}:v{mko.version}",
        "imi_soft_wire": "available_via_gateway",
        "ask_triggered": False,
    }
