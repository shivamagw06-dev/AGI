"""Phase-2 modular licensed consensus collector.

Architecture does NOT assume proprietary analyst estimates.
Returns UNKNOWN / not_configured unless a licensed provider is wired.
Never scrape broker reports. Never fabricate street consensus.
"""

from __future__ import annotations

import os
from typing import Any

from knowledge_factory.market_expectations_intelligence.schema import UNKNOWN

# Optional env flag — only enable when a licensed provider is configured.
LICENSED_CONSENSUS_ENV = "AGIB_LICENSED_CONSENSUS_PROVIDER"


def licensed_consensus_available() -> bool:
    provider = os.environ.get(LICENSED_CONSENSUS_ENV, "").strip()
    return bool(provider)


def collect_licensed_consensus(
    *,
    entity: str | None = None,
    metric: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    """Fetch external consensus only when a licensed provider is configured.

    Default: not configured → UNKNOWN payload (Phase-1 remains complete).
    """
    provider = os.environ.get(LICENSED_CONSENSUS_ENV, "").strip()
    if not provider:
        return {
            "status": "not_configured",
            "phase": 2,
            "provider": UNKNOWN,
            "entity": entity,
            "metric": metric,
            "period": period,
            "consensus": {
                "median": UNKNOWN,
                "mean": UNKNOWN,
                "high": UNKNOWN,
                "low": UNKNOWN,
                "std_dev": UNKNOWN,
                "n_estimates": UNKNOWN,
            },
            "expectations": [],
            "licensed_consensus": False,
            "fabricated": False,
            "note": (
                "Phase-2 licensed consensus collector is modular and inactive. "
                "Set AGIB_LICENSED_CONSENSUS_PROVIDER when a licensed feed is available."
            ),
        }

    # Provider configured but adapter not implemented in this sprint — still UNKNOWN.
    # Keeps architecture open without inventing estimates.
    return {
        "status": "provider_configured_adapter_pending",
        "phase": 2,
        "provider": provider,
        "entity": entity,
        "metric": metric,
        "period": period,
        "consensus": {
            "median": UNKNOWN,
            "mean": UNKNOWN,
            "high": UNKNOWN,
            "low": UNKNOWN,
            "std_dev": UNKNOWN,
            "n_estimates": UNKNOWN,
        },
        "expectations": [],
        "licensed_consensus": False,
        "fabricated": False,
        "note": "Licensed provider name present; adapter not yet implemented — no fabricated estimates.",
    }
