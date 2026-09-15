"""Compile Company Intelligence Object — single structured qualitative source."""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence import store as ici_store
from knowledge_factory.company_intelligence.collectors.soft import collect_company_context
from knowledge_factory.company_intelligence.coverage import compute_coverage_level, intelligence_score
from knowledge_factory.company_intelligence.producers.core import produce_all_modules
from knowledge_factory.company_intelligence.schema import (
    ICI_SCHEMA_VERSION,
    ICI_VERSION,
    LAYER,
    PROGRAMME,
    FREEZE_LOCKS,
)
from knowledge_factory.company_intelligence.validators.gates import validate_object


def compile_company_intelligence(ticker: str, *, persist: bool = True) -> dict[str, Any]:
    t = str(ticker or "").upper()
    ctx = collect_company_context(t)
    modules = produce_all_modules(ctx)

    draft: dict[str, Any] = {
        "kind": "company_intelligence_object",
        "ticker": t,
        "sector": ctx.get("sector"),
        "modules": modules,
        "has_institutional_seed": bool(ctx.get("has_seed")),
        "validation_failed": False,
        "coverage_level": 0,
        "fabricated": False,
    }
    # Gate check independent of Level 7 (use provisional level 6)
    prelim = validate_object({**draft, "coverage_level": 6})
    level_info = compute_coverage_level(modules, gate_pass=bool(prelim.get("gate_pass")))
    draft["coverage_level"] = level_info["coverage_level"]
    draft["coverage_level_name"] = level_info["coverage_level_name"]

    quality = validate_object(draft)
    score = intelligence_score(draft)

    obj = {
        "kind": "company_intelligence_object",
        "ici_version": ICI_VERSION,
        "ici_schema_version": ICI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "ticker": t,
        "sector": ctx.get("sector"),
        "modules": modules,
        "coverage_level": draft["coverage_level"],
        "coverage_level_name": draft["coverage_level_name"],
        "complete": bool(level_info.get("complete")),
        "intelligence_score": score,
        "quality": quality,
        "institutional_ready": bool(quality.get("institutional_ready")),
        "unknown_fields": quality.get("unknown_fields"),
        "has_institutional_seed": bool(ctx.get("has_seed")),
        "sprint": {
            "1a_modules": True,
            "1b_modules": True,
        },
        "freeze_locks": FREEZE_LOCKS,
        "architecture_status": "SOFT_COMPANY_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "fabricated": False,
    }
    if persist:
        ici_store.put(obj)
    return obj
