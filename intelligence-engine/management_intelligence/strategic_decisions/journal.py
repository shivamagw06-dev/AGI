"""Decision journal — major management decisions with expected vs actual."""

from __future__ import annotations

from typing import Any


def decision_journal(profile: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for d in profile.get("capital_allocation") or []:
        rows.append(
            {
                "decision": d.get("decision"),
                "reason": d.get("reason"),
                "expected_outcome": d.get("expected_outcome"),
                "actual_outcome": d.get("actual_outcome"),
                "lessons": d.get("lessons"),
                "value_label": d.get("value_label"),
                "as_of": d.get("as_of"),
                "source_doc": d.get("source_doc"),
            }
        )
    for a in profile.get("acquisitions") or []:
        rows.append(
            {
                "decision": f"Acquisition/merger: {a.get('name')}",
                "reason": a.get("strategic_rationale"),
                "expected_outcome": a.get("synergies_promised"),
                "actual_outcome": a.get("synergies_realised"),
                "lessons": a.get("integration_progress"),
                "value_label": a.get("shareholder_value_impact"),
                "as_of": a.get("as_of"),
            }
        )
    return rows
