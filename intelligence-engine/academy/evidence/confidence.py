"""Explainable confidence decomposition — never a bare percentage."""

from __future__ import annotations

from typing import Any

# Default institutional weights (sum = 1.0)
DEFAULT_WEIGHTS = {
    "evidence": 0.45,      # sourced facts / filings quality
    "historical": 0.20,    # multi-period support
    "peer": 0.20,          # peer benchmark support
    "macro": 0.15,         # macro consistency when relevant
}


def decompose_confidence(
    *,
    evidence: float,
    historical: float,
    peer: float,
    macro: float = 70.0,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return explainable confidence in 0–100 with component contributions.

    Each input score is 0–100 quality of that pillar.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    # renormalize
    s = sum(w.values()) or 1.0
    w = {k: v / s for k, v in w.items()}

    comps = {
        "evidence": max(0.0, min(100.0, float(evidence))),
        "historical": max(0.0, min(100.0, float(historical))),
        "peer": max(0.0, min(100.0, float(peer))),
        "macro": max(0.0, min(100.0, float(macro))),
    }
    contributions = {k: round(comps[k] * w[k], 2) for k in comps}
    total = round(sum(contributions.values()), 2)
    return {
        "confidence": total,
        "breakdown": comps,
        "weights": {k: round(v, 3) for k, v in w.items()},
        "contributions": contributions,
        "formula": "confidence = Σ (pillar_score × weight)",
        "explain": (
            f"Evidence {comps['evidence']:.0f}×{w['evidence']:.0%} + "
            f"Historical {comps['historical']:.0f}×{w['historical']:.0%} + "
            f"Peer {comps['peer']:.0f}×{w['peer']:.0%} + "
            f"Macro {comps['macro']:.0f}×{w['macro']:.0%} = {total:.0f}"
        ),
    }


def score_claim_support(
    *,
    has_sourced_facts: bool,
    n_sources: int,
    has_history: bool,
    has_peers: bool,
    street_named: bool = True,
    is_prior_only: bool = False,
) -> dict[str, Any]:
    """Heuristic pillar scores for a claim bundle."""
    if is_prior_only:
        return decompose_confidence(evidence=25, historical=30, peer=20, macro=50)

    evidence = 40.0
    if has_sourced_facts:
        evidence += 35.0
    evidence += min(20.0, 5.0 * n_sources)
    if not street_named:
        evidence -= 10.0

    historical = 75.0 if has_history else 35.0
    peer = 75.0 if has_peers else 30.0
    macro = 70.0
    return decompose_confidence(
        evidence=evidence, historical=historical, peer=peer, macro=macro
    )
