"""Release observability — presentation only. No engine / governance changes.

PR #309 is the final release of the research-governance programme:

    Knowledge → Decision Engine → Governance Spec → Evaluation Lab
             → Drift Analysis → Release Decision → Observability (this module)

After this merge, freeze governance machinery. Subsequent releases should improve
investment analysis itself (earnings → valuation → ownership → macro), using the
evaluation stack to prove measurable gains — not expand the governance stack.
"""

from __future__ import annotations

OBSERVABILITY_VERSION = "release-observability-v1.0.0"
PROGRAMME = "AGIB_RELEASE_OBSERVABILITY"

# Final governance-programme release. Do not expand this stack further here.
GOVERNANCE_PROGRAMME_STATUS = "frozen_after_pr309"

# Explicit freeze: this module must not alter decision/governance logic.
SCOPE_LOCKS = {
    "decision_engine": "read_only",
    "constitution": "read_only",
    "governance_spec": "read_only",
    "scoring": "read_only",
    "weights": "read_only",
    "reasoning": "read_only",
    "valuation_models": "read_only",
    "technical_models": "read_only",
    "presentation_only": True,
}

# Next programme after governance freeze (not implemented in this PR).
POST_GOVERNANCE_ROADMAP = (
    "earnings_intelligence",
    "valuation_intelligence",
    "ownership_intelligence",
    "macro_intelligence",
)

DECISION_BUCKETS = (
    "High Conviction",
    "Constructive",
    "Neutral",
    "Watchlist",
    "Deferred",
    "Inconclusive",
    "Cautious",
    "Other",
)
