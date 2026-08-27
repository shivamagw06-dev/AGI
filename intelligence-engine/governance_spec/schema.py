"""Governance Specification — policy layer distinct from runner & results.

Architecture:
  Constitution → Governance Specification → Test Runner → Evaluation Results
"""

from __future__ import annotations

from typing import Any

PROGRAMME = "AGIB_GOVERNANCE_SPECIFICATION"
# Frozen active spec — bump only via explicit v1.1 release.
GOVERNANCE_SPEC_VERSION = "v1.0"
GOVERNANCE_SPEC_ID = "governance-spec-v1.0"
FROZEN = True

SEVERITIES = ("Critical", "High", "Medium", "Low")

# Active specification pin
ACTIVE_SPEC = GOVERNANCE_SPEC_VERSION


def rule(
    rule_id: str,
    *,
    assertion: str,
    severity: str,
    description: str = "",
    applies_when: str = "always",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "assertion": assertion,
        "severity": severity,
        "description": description,
        "applies_when": applies_when,
        "spec_version": GOVERNANCE_SPEC_VERSION,
    }
