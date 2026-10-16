"""Persistent company Thesis DNA — compare the current thesis with durable traits."""

from __future__ import annotations

import hashlib
from typing import Any

_KNOWN_DNA: dict[str, list[str]] = {
    "apple": ["Premium Ecosystem", "Recurring Revenue", "Pricing Power", "Capital Allocation", "Innovation"],
    "tcs": ["Asset Light", "Cash Generation", "Talent", "Delivery", "Execution"],
    "hdfc bank": ["Funding Franchise", "Risk Discipline", "Distribution", "Capital Strength", "Execution"],
    "infosys": ["Asset Light", "Cash Generation", "Global Delivery", "Talent", "Digital Transformation"],
    "reliance": ["Scale", "Integration", "Capital Allocation", "Consumer Platforms", "Execution"],
}


def build_thesis_dna(
    entity: str,
    pillars: list[dict[str, Any]],
    *,
    thesis_breaking_conditions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    key = (entity or "the subject").strip().lower()
    traits = list(_KNOWN_DNA.get(key) or [])
    if not traits:
        ranked = sorted(pillars, key=lambda p: -float(p.get("strength") or 0.5))
        traits = [p["pillar"] for p in ranked[:5]]

    pillar_vector = {
        p["pillar"]: round(float(p.get("strength") or 0.5), 4) for p in pillars
    }
    aligned = [
        {
            "trait": trait,
            "alignment": round(
                max(
                    pillar_vector.values(),
                    default=0.5,
                )
                if trait not in pillar_vector
                else pillar_vector[trait],
                4,
            ),
        }
        for trait in traits
    ]
    raw = f"{key}|{'|'.join(traits)}|" + "|".join(
        f"{name}:{value:.2f}" for name, value in sorted(pillar_vector.items())
    )
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    mean_alignment = sum(x["alignment"] for x in aligned) / max(len(aligned), 1)
    return {
        "entity": entity,
        "persistent_traits": traits,
        "trait_alignment": aligned,
        "alignment_score": round(mean_alignment, 4),
        "alignment_pct": round(mean_alignment * 100),
        "pillar_vector": pillar_vector,
        "breaking_conditions": [
            b.get("condition") for b in (thesis_breaking_conditions or [])[:4]
        ],
        "fingerprint": fingerprint,
        "source": "known_company_dna" if key in _KNOWN_DNA else "derived_from_pillars",
    }
