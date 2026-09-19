"""IAP selection quality gates."""

from __future__ import annotations

from typing import Any


def validate_selection(
    playbook: dict[str, Any],
    *,
    checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    if not playbook.get("playbook_id"):
        failures.append("missing_playbook_id")
    if not playbook.get("checklist"):
        failures.append("missing_checklist")
    if not playbook.get("procedure"):
        failures.append("missing_procedure")
    if not playbook.get("frameworks"):
        failures.append("missing_frameworks")
    if not playbook.get("output_structure"):
        failures.append("missing_output_structure")
    if checklist is not None and not (checklist.get("steps") or []):
        failures.append("empty_expanded_checklist")

    return {
        "passed": not failures,
        "failures": failures,
        "has_common_mistakes": bool(playbook.get("common_mistakes")),
        "has_evidence_required": bool(playbook.get("evidence_required")),
        "fabricated": False,
    }
