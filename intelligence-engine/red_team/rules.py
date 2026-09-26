"""Red Team operating rules — prevent benchmark overfitting."""

from __future__ import annotations

RED_TEAM_RULES: tuple[str, ...] = (
    "Never reuse previous benchmarks (gold, phase-2, adversarial chaos banks).",
    "Never tell the reasoning engine what family a question belongs to.",
    "Mix multiple reasoning families into one prompt when possible.",
    "Change wording every time a category is re-tested.",
    "Include incomplete, conflicting and misleading evidence.",
    "Measure why AIG failed, not just whether it failed.",
    "Every new capability must first fail on a new adversarial test before production.",
    "Red Team prompts are evaluation-only and must never be imported into matchers or composers.",
)

CAPABILITY_GATE_RULE = (
    "Every new capability must first fail on a new adversarial test before it is allowed into production."
)
