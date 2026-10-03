"""Uncertainty engine — classify known / known-unknown / weak / conflicting / unknown-unknown."""

from __future__ import annotations

from typing import Any

from decision_engine_v2.schema import UNCERTAINTY_CLASSES


def classify_uncertainty(
    inputs: dict[str, Any],
    *,
    conflicts: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    coverage = float(evidence.get("coverage") or inputs.get("coverage") or 0)
    classes: list[dict[str, Any]] = []

    classes.append(
        {
            "class": "known",
            "items": [i["layer"] for i in (evidence.get("items") or []) if i.get("present") and i.get("signal") is not None],
        }
    )
    missing = [i["layer"] for i in (evidence.get("items") or []) if not i.get("present")]
    if missing:
        classes.append({"class": "known_unknown", "items": missing})
    weak = [i["layer"] for i in (evidence.get("items") or []) if i.get("present") and i.get("signal") is None]
    if weak:
        classes.append({"class": "weak_evidence", "items": weak})
    if conflicts.get("conflict_count", 0) > 0:
        classes.append(
            {
                "class": "conflicting_evidence",
                "items": [c.get("type") for c in (conflicts.get("conflicts") or [])],
            }
        )
    # Residual unknown-unknown: always disclosed when coverage < 1
    if coverage < 0.99:
        classes.append(
            {
                "class": "unknown_unknown",
                "items": ["unmodelled regime shifts", "private information not in filings"],
            }
        )

    present_classes = {c["class"] for c in classes}
    return {
        "classes": classes,
        "disclosed": True,
        "coverage": coverage,
        "dominant": (
            "conflicting_evidence"
            if "conflicting_evidence" in present_classes
            else "known_unknown"
            if "known_unknown" in present_classes
            else "weak_evidence"
            if "weak_evidence" in present_classes
            else "known"
        ),
        "available_classes": list(UNCERTAINTY_CLASSES),
        "rule": "Decision quality depends on disclosed uncertainty — never silent",
    }
