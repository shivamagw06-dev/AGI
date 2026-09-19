"""Module 5 — Scenario Intelligence.

Every recommendation carries bull/base/bear/stress plus named macro shocks.
"""

from __future__ import annotations

from typing import Any

SCENARIO_VERSION = "scenario-intelligence-v1.0.0"

_SHOCKS = (
    ("fed_plus_100bp", "Fed +100bp", -0.08, 0.15),
    ("fed_minus_100bp", "Fed -100bp", 0.06, 0.15),
    ("oil_plus_20", "Oil +20%", -0.04, 0.12),
    ("inr_minus_10", "INR -10%", 0.03, 0.10),
    ("us_recession", "US Recession", -0.18, 0.12),
    ("india_recession", "India Recession", -0.22, 0.10),
    ("ai_capex_slowdown", "AI Capex Slowdown", -0.14, 0.18),
)


def compute_scenarios(
    *,
    entity_id: str | None,
    downside: dict[str, Any] | None = None,
    exposure: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    downside = downside or {}
    exposure = exposure or {}
    evidence = evidence or {}
    sector = str(((exposure.get("exposure") or {}).get("sector")) or "")
    theme = str(((exposure.get("exposure") or {}).get("theme")) or "")

    base = downside.get("base_case") or {"expected_return": 0.0, "probability": 0.45, "confidence": 0.7}
    bull = downside.get("bull_case") or {"expected_return": 0.12, "probability": 0.2, "confidence": 0.6}
    bear = downside.get("bear_case") or {"expected_return": -0.15, "probability": 0.25, "confidence": 0.7}
    stress = downside.get("stress_case") or {"expected_return": -0.30, "probability": 0.1, "confidence": 0.55}

    shocks = []
    for sid, label, ret, prob in _SHOCKS:
        adj = ret
        affected = ["rel_val_damodaran", "hist_multiples"]
        if sid == "ai_capex_slowdown" and ("it" in sector or theme == "ai_services"):
            adj = min(adj, -0.18)
            affected.append("business_quality")
        if sid == "india_recession":
            affected.append("margin_of_safety")
        shocks.append(
            {
                "id": sid,
                "label": label,
                "expected_return": adj,
                "expected_loss": round(abs(min(0.0, adj)), 4),
                "probability": prob,
                "confidence": 0.62,
                "affected_frameworks": affected,
            }
        )

    scenarios = {
        "bull": {
            "expected_return": bull.get("expected_return"),
            "expected_loss": 0.0,
            "probability": bull.get("probability"),
            "confidence": bull.get("confidence"),
            "affected_frameworks": ["rel_val_damodaran", "hist_multiples"],
        },
        "base": {
            "expected_return": base.get("expected_return"),
            "expected_loss": 0.0,
            "probability": base.get("probability"),
            "confidence": base.get("confidence"),
            "affected_frameworks": ["rel_val_damodaran", "hist_multiples", "margin_of_safety"],
        },
        "bear": {
            "expected_return": bear.get("expected_return") if isinstance(bear, dict) else bear,
            "expected_loss": round(abs(min(0.0, float((bear or {}).get("expected_return") or bear or 0))), 4)
            if isinstance(bear, dict)
            else round(abs(min(0.0, float(bear or 0))), 4),
            "probability": (bear or {}).get("probability") if isinstance(bear, dict) else 0.25,
            "confidence": (bear or {}).get("confidence") if isinstance(bear, dict) else 0.7,
            "affected_frameworks": ["rel_val_damodaran", "hist_multiples", "margin_of_safety"],
        },
        "stress": {
            "expected_return": stress.get("expected_return") if isinstance(stress, dict) else stress,
            "expected_loss": round(
                abs(min(0.0, float((stress or {}).get("expected_return") if isinstance(stress, dict) else stress or 0))),
                4,
            ),
            "probability": (stress or {}).get("probability") if isinstance(stress, dict) else 0.1,
            "confidence": (stress or {}).get("confidence") if isinstance(stress, dict) else 0.55,
            "affected_frameworks": ["rel_val_damodaran", "dcf_applicability", "margin_of_safety"],
        },
    }

    return {
        "found": True,
        "scenario_version": SCENARIO_VERSION,
        "entity_id": entity_id,
        "scenarios": scenarios,
        "scenario_set": scenarios,
        "shocks": shocks,
        "current_pe": evidence.get("current_pe"),
    }
