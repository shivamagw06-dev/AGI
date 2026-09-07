"""Expected contribution scores — adaptive learning hook for ILM."""

from __future__ import annotations

from typing import Any

from layer_router.registry import LAYER_DEFS


def expected_contributions(
    required: list[str],
    optional: list[str],
    suppressed: list[str],
    importance: dict[str, int],
    *,
    primary_objective: str | None = None,
) -> list[dict[str, Any]]:
    """Return per-layer expected contribution table (runs? / % / reason)."""
    rows: list[dict[str, Any]] = []
    # Weight importance among running layers
    running = list(required) + [x for x in optional if x not in required]
    imp_sum = sum(max(1, int(importance.get(x, 1))) for x in required) or 1
    for layer in running:
        share = max(1, int(importance.get(layer, 1))) / imp_sum if layer in required else 0.0
        # Blend registry confidence contribution with importance share
        reg = float((LAYER_DEFS.get(layer) or {}).get("confidence_contribution") or 0.03)
        expected = round((share * 0.7 + reg * 0.3) if layer in required else 0.0, 4)
        # Renormalize later
        rows.append(
            {
                "layer": layer,
                "runs": layer in required or layer in optional,
                "required": layer in required,
                "expected_contribution": expected,
                "reason": _reason(layer, primary_objective, required=layer in required),
            }
        )
    # Normalize required expected to sum 1.0
    req_rows = [r for r in rows if r["required"]]
    total = sum(r["expected_contribution"] for r in req_rows) or 1.0
    for r in req_rows:
        r["expected_contribution"] = round(r["expected_contribution"] / total, 4)
    drift = round(1.0 - sum(r["expected_contribution"] for r in req_rows), 4)
    if req_rows:
        req_rows[0]["expected_contribution"] = round(req_rows[0]["expected_contribution"] + drift, 4)

    for layer in suppressed:
        rows.append(
            {
                "layer": layer,
                "runs": False,
                "required": False,
                "expected_contribution": 0.0,
                "reason": _suppress_reason(layer, primary_objective),
            }
        )

    # Dict form for confidence engine
    by_layer = {r["layer"]: r["expected_contribution"] for r in rows if r["required"]}
    return {
        "expected_contributions": rows,
        "expected_contribution_by_layer": by_layer,
        "learning_hook": {
            "compare_after_execution": True,
            "feed_into": "ILM",
            "note": "Compare expected vs actual contribution to adapt future routing.",
        },
    }


def _reason(layer: str, objective: str | None, *, required: bool) -> str:
    reasons = {
        "FIL": "Official filings required",
        "EIL": "Evidence ranking critical",
        "PIL": "Relative valuation / peer context needed",
        "CIG": "Macro transmission relevant",
        "ILM": "Prior thesis useful",
        "FDI": "Filing changes informative",
        "ACI": "Earnings quality check",
        "FIE": "Forward path required",
        "IKG": "Entity relationships useful",
        "Business": "Business quality central to decision",
        "Financial": "Financial strength central",
        "Valuation": "Valuation judgement required",
        "Risk": "Downside mapping required",
        "Portfolio": "Portfolio fit required",
        "Committee": "Institutional synthesis required",
        "IDE V2": "Decision packaging required",
        "CIO": "Final decision framing",
        "Research Writer": "Report assembly",
        "Macro": "Macro impulse relevant",
        "Sector": "Sector context relevant",
        "SSL": "Simulation requested",
        "MII": "Management evidence useful",
        "Management": "Management assessment relevant",
        "Ownership": "Ownership structure relevant",
    }
    if not required:
        return f"Optional for {objective or 'this objective'}"
    return reasons.get(layer, f"Supports {objective or 'research objective'}")


def _suppress_reason(layer: str, objective: str | None) -> str:
    defaults = {
        "SSL": "No simulation requested",
        "MII": "Management quality not central",
        "Ownership": "Not relevant",
        "Management": "Not central to question",
        "Portfolio": "Portfolio context not required",
        "Business": "Business deep-dive not required",
    }
    return defaults.get(layer, f"Below importance threshold for {objective or 'objective'}")
