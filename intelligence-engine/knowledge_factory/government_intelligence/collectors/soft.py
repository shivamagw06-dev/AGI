"""Soft collectors — Phase 1 high-impact seeds + registries only.

Never infer policy. Phase 2+ domains remain architectural extension points.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.fixtures.seeds import all_policy_seeds
from knowledge_factory.government_intelligence.ministry_registry.catalog import list_ministries
from knowledge_factory.government_intelligence.regulators.catalog import list_regulators
from knowledge_factory.government_intelligence.schema import (
    DELIVERY_PHASE,
    PHASE_1_DOMAINS,
    PHASE_2_EXTENSIBLE_DOMAINS,
)


def collect_government_context(*, include_extensible: bool = False) -> dict[str, Any]:
    ministries = list_ministries(phase="phase_1")
    regulators = list_regulators(phase="phase_1")
    seeds = all_policy_seeds()
    if include_extensible:
        from knowledge_factory.government_intelligence.fixtures.extensible_seeds import (
            extensible_policy_seeds,
        )
        from knowledge_factory.government_intelligence.ministry_registry.catalog import (
            list_ministries as _lm,
        )
        from knowledge_factory.government_intelligence.regulators.catalog import (
            list_regulators as _lr,
        )

        ministries = _lm(phase="all")
        regulators = _lr(phase="all")
        seeds = seeds + extensible_policy_seeds()

    return {
        "delivery_phase": DELIVERY_PHASE,
        "phase_1_domains": list(PHASE_1_DOMAINS),
        "phase_2_extensible_domains": list(PHASE_2_EXTENSIBLE_DOMAINS),
        "ministries": ministries,
        "regulators": regulators,
        "policy_seeds": seeds,
        "sources_priority": [
            "government_of_india",
            "rbi",
            "sebi",
            "gst_council",
            "pib",
            "ministry_of_finance",
            "ministry_of_commerce",
            "official_gazette",
            "official_notifications",
            "parliamentary_documents",
        ],
        "never_infer_policy": True,
        "never_fabricate": True,
        "include_extensible": include_extensible,
    }
