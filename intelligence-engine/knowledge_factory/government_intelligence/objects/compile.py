"""Compile Government & Regulatory Intelligence pack."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence import store as igri_store
from knowledge_factory.government_intelligence.collectors.soft import collect_government_context
from knowledge_factory.government_intelligence.coverage import compute_coverage_level
from knowledge_factory.government_intelligence.producers.core import produce_all
from knowledge_factory.government_intelligence.schema import (
    DELIVERY_PHASE,
    FREEZE_LOCKS,
    IGRI_VERSION,
    LAYER,
    PHASE_1_DOMAINS,
    PHASE_2_EXTENSIBLE_DOMAINS,
    PROGRAMME,
)
from knowledge_factory.government_intelligence.timeline.build import build_policy_timeline
from knowledge_factory.government_intelligence.validators.gates import validate_pack


def compile_government_intelligence(*, persist: bool = True) -> dict[str, Any]:
    ctx = collect_government_context(include_extensible=False)
    produced = produce_all(ctx)
    bodies = produced["bodies"]
    policies = produced["policies"]
    # Stamp Phase 1
    for p in policies:
        p["delivery_phase"] = "phase_1"
    timeline = build_policy_timeline(policies)
    quality = validate_pack(bodies=bodies, policies=policies, timeline=timeline)
    level = compute_coverage_level(
        bodies=bodies, policies=policies, timeline=timeline, quality=quality
    )

    from knowledge_factory.government_intelligence.validators.gates import validate_policy

    for p in policies:
        p["validation"] = validate_policy(p)

    domains = sorted({str(p.get("domain") or "") for p in policies})
    pack = {
        "kind": "government_intelligence_pack",
        "igri_version": IGRI_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "delivery_phase": DELIVERY_PHASE,
        "phase_1_domains": list(PHASE_1_DOMAINS),
        "phase_2_extensible_domains": list(PHASE_2_EXTENSIBLE_DOMAINS),
        "phase_1_complete": set(PHASE_1_DOMAINS).issubset(set(domains)) and bool(quality.get("gate_pass")),
        "registry": {
            "bodies": bodies,
            "body_count": len(bodies),
            "phase": "phase_1",
        },
        "policies": policies,
        "policy_count": len(policies),
        "timeline": timeline,
        "domains": domains,
        "quality": quality,
        "coverage_level": level["coverage_level"],
        "coverage_level_name": level["coverage_level_name"],
        "complete": level["complete"],
        "institutional_ready": bool(quality.get("institutional_ready")),
        "freeze_locks": FREEZE_LOCKS,
        "architecture_status": "SOFT_GOVERNMENT_REGULATORY_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "political_opinion": False,
        "policy_forecast": False,
        "fabricated": False,
        "extension_note": (
            "MCA, other industry regulators, and state policies are architectural "
            "extension points — not required for Phase 1 exit."
        ),
    }
    if persist:
        for b in bodies:
            igri_store.put_body(b)
        for p in policies:
            igri_store.put_policy(p)
        igri_store.put_timeline(timeline)
    return pack
