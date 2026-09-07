"""AGIB v3.5 — Institutional Analytical Playbooks (IAP)."""

from institutional_playbooks.schema import IAP_VERSION, MODULE_CODE, PROGRAMME
from institutional_playbooks.selector.engine import select_playbook

__all__ = [
    "IAP_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "select_playbook",
]
