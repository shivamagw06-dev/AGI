"""IFAC API surface — composition layer, not an intelligence engine."""

from __future__ import annotations

from typing import Any, Optional

from intelligence_fusion_answer_composer.compose import compose
from intelligence_fusion_answer_composer.models import LAYER, TEMPLATE_IDS, VERSION
from intelligence_fusion_answer_composer.priorities import FAMILY_PRIORITY
from intelligence_fusion_answer_composer import store as ifac_store
from intelligence_fusion_answer_composer.templates import TEMPLATES


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "layer": LAYER,
        "version": VERSION,
        "role": "intelligence_fusion_answer_composer",
        "generates_intelligence": False,
        "vendor_calls": False,
        "recommendation_language": False,
        "templates": list(TEMPLATE_IDS),
        "families": sorted(FAMILY_PRIORITY),
        "endpoints": [
            "/v1/ifac/health",
            "/v1/ifac/compose",
            "/v1/ifac/templates",
            "/v1/ifac/routing",
            "/v1/ifac/confidence",
            "/v1/ifac/debug",
            "/v1/ifac/provenance",
            "/v1/ifac/dashboard",
        ],
        "note": (
            "IFAC fuses warehouse-backed engine outputs into institutional reports. "
            "It never recalculates valuation or calls vendors."
        ),
        "stats": ifac_store.stats(),
    }


def templates_catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "layer": LAYER,
        "templates": {
            tid: [{"id": s[0], "title": s[1], "engines": list(s[2])} for s in secs]
            for tid, secs in TEMPLATES.items()
        },
    }


def routing_table() -> dict[str, Any]:
    return {
        "ok": True,
        "layer": LAYER,
        "routing": {
            fam: {
                "primary": list(pack.get("primary") or ()),
                "secondary": list(pack.get("secondary") or ()),
                "supporting": list(pack.get("supporting") or ()),
                "reference": list(pack.get("reference") or ()),
            }
            for fam, pack in FAMILY_PRIORITY.items()
        },
        "rule": "External consensus is reference-only and must never be the executive headline.",
    }


def confidence_board() -> dict[str, Any]:
    stats = ifac_store.stats()
    return {
        "ok": True,
        "layer": LAYER,
        "aggregation": "primary-weighted mean; consensus weight 0.25",
        "stats": stats,
        "recent": ifac_store.recent(12),
    }


def debug_last(limit: int = 20) -> dict[str, Any]:
    return {
        "ok": True,
        "layer": LAYER,
        "recent": ifac_store.recent(limit),
        "stats": ifac_store.stats(),
    }


def provenance_sample() -> dict[str, Any]:
    recent = ifac_store.recent(1)
    return {
        "ok": True,
        "layer": LAYER,
        "schema": {
            "primary_engine": "str",
            "supporting_engines": ["str"],
            "reference_engines": ["str"],
            "warehouse_tables": ["str"],
            "confidence": "float",
            "timestamp": "iso8601",
        },
        "latest": recent[0] if recent else None,
    }


def dashboard() -> dict[str, Any]:
    stats = ifac_store.stats()
    return {
        "ok": True,
        "layer": LAYER,
        "version": VERSION,
        "stats": stats,
        "recent": ifac_store.recent(20),
        "routing": routing_table().get("routing"),
        "templates": list(TEMPLATE_IDS),
        "success_targets": {
            "institutional_template_usage": "100%",
            "consensus_first_responses": "0%",
            "explainability_coverage": "100%",
            "avg_compose_ms": "<500",
        },
    }


def compose_api(payload: dict[str, Any]) -> dict[str, Any]:
    body = payload or {}
    return compose(
        question=str(body.get("question") or ""),
        family=body.get("family"),
        provider_results=list(body.get("provider_results") or body.get("engines") or []),
        ticker=body.get("ticker"),
        fused=body.get("fused") if isinstance(body.get("fused"), dict) else {},
    )
