"""IFSE quality gates."""

from __future__ import annotations

from typing import Any

from framework_selection.rules.forbidden import COMPOSITION_RULES, is_forbidden


def validate_selection(
    *,
    selected: list[dict[str, Any]],
    sector: str | None,
    confidence: dict[str, Any],
    dropped_replay: list[str] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    ids = {str(r.get("framework_id")) for r in selected}

    if not selected:
        failures.append("missing_framework")

    for row in selected:
        fid = str(row.get("framework_id"))
        if is_forbidden(fid, sector=sector):
            failures.append(f"forbidden_framework:{fid}")

    for rule in COMPOSITION_RULES:
        if rule.get("sector") and rule["sector"] != sector:
            continue
        only = rule.get("reject_if_only")
        if only and ids and ids.issubset(only):
            failures.append(f"wrong_framework:{rule['id']}")
        require_any = rule.get("require_any")
        if require_any and not (ids & set(require_any)):
            # Only fail when sector-bound valuation frameworks were attempted
            if any(r.get("role") == "primary" for r in selected):
                failures.append(f"framework_conflict:{rule['id']}")
        single_only = rule.get("reject_if_single_multiple_only")
        if single_only and ids and ids.issubset(single_only) and len(ids) == 1:
            failures.append(f"wrong_framework:{rule['id']}")

    # Primary conflicts: EV/EBITDA + banks already caught by forbidden
    primaries = [r for r in selected if r.get("role") == "primary"]
    if sector == "banks" and any(r.get("framework_id") == "FW_EV_EBITDA" for r in primaries):
        failures.append("wrong_framework:banks_ev_ebitda")

    conf_score = float((confidence or {}).get("score") or 0)
    if conf_score > 1.0 or conf_score < 0.0:
        failures.append("confidence_impossible")

    if dropped_replay and not selected:
        failures.append("replay_mismatch")

    failures = sorted(set(failures))
    return {
        "passed": not failures,
        "failures": failures,
        "fabricated": False,
    }
