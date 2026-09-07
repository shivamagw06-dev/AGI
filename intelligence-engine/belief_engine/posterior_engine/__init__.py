"""Posterior engine — Bayesian log-odds update from prior + evidence LRs."""

from __future__ import annotations

import math
from typing import Any

from belief_engine.schema import BELIEF_STATES


def _clamp(p: float) -> float:
    return round(max(0.05, min(0.95, float(p))), 4)


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    # numerically stable
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def belief_state_from_posterior(posterior: float) -> str:
    p = float(posterior)
    if p >= 0.8:
        return "Strongly Supported"
    if p >= 0.68:
        return "Supported"
    if p >= 0.58:
        return "Leaning Positive"
    if p >= 0.45:
        return "Neutral"
    if p >= 0.38:
        return "Leaning Negative"
    if p >= 0.28:
        return "Challenged"
    if p >= 0.18:
        return "Contradicted"
    return "Rejected"


def update_posterior(prior: float, log_lr_total: float) -> dict[str, Any]:
    prior = _clamp(prior)
    logit_post = _logit(prior) + float(log_lr_total)
    posterior = _clamp(_sigmoid(logit_post))
    state = belief_state_from_posterior(posterior)
    assert state in BELIEF_STATES
    return {
        "prior_belief": prior,
        "log_odds_prior": round(_logit(prior), 4),
        "log_likelihood_total": round(float(log_lr_total), 4),
        "log_odds_posterior": round(logit_post, 4),
        "posterior_belief": posterior,
        "posterior_belief_pct": round(posterior * 100),
        "delta": round(posterior - prior, 4),
        "belief_state": state,
        "update_rule": "logit(posterior) = logit(prior) + Σ log LR(evidence, falsification)",
    }
