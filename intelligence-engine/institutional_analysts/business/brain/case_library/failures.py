"""Counter-cases / failure studies — knowledge assets, not engines."""

from __future__ import annotations

from typing import Any

FAILURE_CASES: list[dict[str, Any]] = [
    {
        "id": "kodak",
        "name": "Kodak",
        "archetype_hints": ["disruption_victim"],
        "drivers": ["Technology leadership ignored", "Incumbent inertia"],
        "chain": ["Ignored disruption", "Business collapsed", "Lesson"],
        "outcome": "Category leadership eroded when disruption was recognised too late.",
        "lessons": [
            "Technology leadership does not guarantee survival.",
            "Protecting the legacy profit pool can destroy the franchise.",
        ],
        "signals": ("disrupt", "technolog", "legacy", "digital transition", "incumbent"),
    },
    {
        "id": "nokia",
        "name": "Nokia",
        "archetype_hints": ["disruption_victim", "consumer_internet"],
        "drivers": ["Dominant market share", "Weak ecosystem", "Lost advantage"],
        "chain": ["Dominant market share", "Weak ecosystem", "Lost advantage"],
        "outcome": "Share leadership collapsed without a durable application/ecosystem moat.",
        "lessons": [
            "Market share is not a moat if customers can switch ecosystems cheaply.",
            "Hardware dominance without platform lock-in is perishable.",
        ],
        "signals": ("market share", "ecosystem", "platform", "switch", "handset", "device"),
    },
    {
        "id": "kingfisher",
        "name": "Kingfisher Airlines",
        "archetype_hints": ["capital_destroyer"],
        "drivers": ["Brand", "Weak capital allocation", "Failure"],
        "chain": ["Brand", "Weak capital allocation", "Failure"],
        "outcome": "Brand strength could not offset poor capital allocation and fragile unit economics.",
        "lessons": [
            "Brand without capital discipline is not an investable franchise.",
            "High fixed-cost models punish weak balance-sheet and allocation choices.",
        ],
        "signals": ("brand", "capital allocation", "debt", "airline", "cash burn", "leverage"),
    },
    {
        "id": "general_electric",
        "name": "General Electric",
        "archetype_hints": ["capital_destroyer"],
        "drivers": ["Complexity", "Financial engineering", "Weak allocation clarity"],
        "chain": ["Conglomerate complexity", "Allocation drift", "Value destruction"],
        "outcome": "Scale and legacy prestige did not prevent capital-allocation drift from impairing the franchise.",
        "lessons": [
            "Complexity without transparent capital discipline erodes institutional trust.",
            "Financial engineering is not a substitute for operating franchise quality.",
        ],
        "signals": ("conglomerate", "complexity", "financial engineering", "allocation drift", "leverage"),
    },
]
