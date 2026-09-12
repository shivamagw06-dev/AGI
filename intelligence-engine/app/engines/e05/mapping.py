"""E05 P0 event taxonomy, decay half-lives, and Feature Registry bindings."""

from __future__ import annotations

MODEL_VERSION = "e05-p0-event-driven-0.1.0"
ENGINE_VERSION = "1.0.0"
FORMULA_ID = "EM_AGI_EVENT"

# P0 event types (frozen WBS) — no M&A deal-prob / activist / distress models
P0_EVENT_TYPES: tuple[str, ...] = (
    "earn_q",
    "earn_fy",
    "earn_surprise",
    "eps_surprise",
    "rev_surprise",
    "guidance",
    "dividend",
    "bonus",
    "split",
    "rights",
    "buyback",
    "pref_issue",
)

# Default decay half-lives (trading days)
HALF_LIFE_DAYS: dict[str, float] = {
    "earn_q": 10.0,
    "earn_fy": 15.0,
    "earn_surprise": 10.0,
    "eps_surprise": 10.0,
    "rev_surprise": 10.0,
    "guidance": 15.0,
    "dividend": 5.0,
    "bonus": 5.0,
    "split": 3.0,
    "rights": 10.0,
    "buyback": 20.0,
    "pref_issue": 15.0,
}

# Relative importance priors in [0, 1]
IMPORTANCE: dict[str, float] = {
    "earn_q": 0.90,
    "earn_fy": 0.92,
    "earn_surprise": 0.95,
    "eps_surprise": 0.95,
    "rev_surprise": 0.85,
    "guidance": 0.78,
    "dividend": 0.55,
    "bonus": 0.50,
    "split": 0.45,
    "rights": 0.65,
    "buyback": 0.70,
    "pref_issue": 0.60,
}

REGISTRY_EVENT: tuple[str, ...] = (
    "EVENT_EPS_SURPRISE",
    "EVENT_GUIDANCE_DELTA",
)

# Lookahead / calendar window for upcoming vs recent
UPCOMING_WINDOW_DAYS = 45
RECENT_WINDOW_DAYS = 60
