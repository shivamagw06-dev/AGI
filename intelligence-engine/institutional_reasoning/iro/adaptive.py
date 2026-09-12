"""Module 4 — Adaptive Planning.

When required evidence is unavailable, the planner substitutes a valid
alternative route rather than stopping. If every route fails, it withholds.
"""

from __future__ import annotations

from typing import Any

ADAPTIVE_VERSION = "adaptive-planning-v1.0.0"

# Ordered alternative routes per blocked evidence field.
_ROUTES: dict[str, tuple[dict[str, Any], ...]] = {
    "historical_pe": (
        {
            "route": "sector_valuation",
            "question": "Is {name} sector expensive versus history?",
            "rationale": "Own-history PE unavailable — fall back to sector valuation history",
        },
        {
            "route": "peer_valuation",
            "question": "How does {name} compare with peers on valuation?",
            "rationale": "Sector history unavailable — fall back to peer-relative valuation",
        },
    ),
    "historical_percentile": (
        {
            "route": "sector_valuation",
            "question": "Is {name} sector expensive versus history?",
            "rationale": "Own percentile unavailable — use sector valuation position",
        },
        {
            "route": "peer_valuation",
            "question": "How does {name} compare with peers on valuation?",
            "rationale": "Use peer percentile instead of own-history percentile",
        },
    ),
    "peer_pe": (
        {
            "route": "sector_valuation",
            "question": "Is {name} sector expensive versus history?",
            "rationale": "Peer multiple unavailable — use sector multiple",
        },
    ),
    "current_pe": (
        {
            "route": "ev_sales",
            "question": "Compare EV/EBITDA vs PE for {name}.",
            "rationale": "PE unusable (negative or missing earnings) — switch to EV-based multiple",
        },
    ),
}

# Negative-earnings style conditions that invalidate PE outright.
_PE_INVALIDATING_REASONS = {
    "placeholder_value",
    "impossible_negative_multiple",
    "impossible_percentile",
}


def routes_for(missing: list[str], rejected: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Ordered alternative routes for the blocked fields."""
    rejected = rejected or {}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # PE invalidated by an impossible value must switch multiple family first.
    for field, reason in rejected.items():
        if field in {"current_pe", "forward_pe"} and str(reason) in _PE_INVALIDATING_REASONS:
            for route in _ROUTES.get("current_pe", ()):
                if route["route"] not in seen:
                    seen.add(route["route"])
                    out.append({**route, "trigger": f"{field}:{reason}"})

    for field in missing:
        for route in _ROUTES.get(field, ()):
            if route["route"] in seen:
                continue
            seen.add(route["route"])
            out.append({**route, "trigger": field})
    return out


def adapt_task(
    *,
    task_label: str,
    entity_name: str,
    missing: list[str],
    rejected: dict[str, Any] | None,
    run_question,
) -> dict[str, Any]:
    """Try alternative routes in order; return the first that executes.

    `run_question(question)` must return a governance record.
    """
    ladder = routes_for(missing, rejected)
    # The full fallback ladder is reported even when an early route succeeds, so
    # the replan is auditable rather than only showing the winning route.
    considered = [
        {
            "route": r["route"],
            "question": r["question"].format(name=entity_name),
            "rationale": r["rationale"],
            "trigger": r.get("trigger"),
        }
        for r in ladder
    ]
    attempts: list[dict[str, Any]] = []
    for route in ladder:
        question = route["question"].format(name=entity_name)
        record = run_question(question)
        executed = any(
            f.get("status") == "executed" for f in (record.get("frameworks") or [])
        )
        attempts.append(
            {
                "route": route["route"],
                "question": question,
                "rationale": route["rationale"],
                "trigger": route.get("trigger"),
                "executed": executed,
            }
        )
        if executed:
            return {
                "adapted": True,
                "route": route["route"],
                "question": question,
                "rationale": route["rationale"],
                "record": record,
                "attempts": attempts,
                "routes_considered": considered,
                "adaptive_version": ADAPTIVE_VERSION,
            }
    return {
        "adapted": False,
        "reason": "all_alternative_routes_exhausted" if attempts else "no_alternative_route",
        "attempts": attempts,
        "routes_considered": considered,
        "withhold": True,
        "adaptive_version": ADAPTIVE_VERSION,
    }
