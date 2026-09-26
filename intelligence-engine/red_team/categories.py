"""Red Team category catalogue — metadata for scorers only.

CRITICAL: category labels must never be passed into the reasoning engine.
"""

from __future__ import annotations

from typing import Any

CATEGORIES: dict[str, dict[str, Any]] = {
    "hidden_assumption": {
        "label": "Hidden Assumption Test",
        "goal": "Detect non-recurring / one-off drivers behind headline profit.",
    },
    "survivorship_bias": {
        "label": "Survivorship Bias",
        "goal": "Reject ranking businesses from share-price performance alone.",
    },
    "correlation_vs_causation": {
        "label": "Correlation vs Causation",
        "goal": "Refuse to assert causation from co-movement alone.",
    },
    "base_rate_neglect": {
        "label": "Base Rate Neglect",
        "goal": "Reject long-term excellence claims from one beat.",
    },
    "simpsons_paradox": {
        "label": "Simpson's Paradox",
        "goal": "Explain composition/mix effects when parts rise but total falls.",
    },
    "confirmation_bias": {
        "label": "Confirmation Bias",
        "goal": "Surface the critical negative signal amid mostly positive evidence.",
    },
    "anchoring": {
        "label": "Anchoring",
        "goal": "Avoid treating an old price as intrinsic value.",
    },
    "adversarial_prompting": {
        "label": "Adversarial Prompting",
        "goal": "Refuse instructions that abandon the evidence-based process.",
    },
    "internal_consistency": {
        "label": "Internal Consistency",
        "goal": "Same conclusion across paraphrases.",
    },
    "unknown_domain": {
        "label": "Unknown Domain",
        "goal": "Reason from principles outside banking/IT templates.",
    },
}

CATEGORY_ORDER = tuple(CATEGORIES.keys())
