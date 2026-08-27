"""Institutional Playbook Framework v1.0."""

from institutional_playbook_framework.production import apply_institutional_playbook_framework, health
from institutional_playbook_framework.registry import get_playbook, list_playbook_keys, registry_summary
from institutional_playbook_framework.resolver import resolve_playbook

__all__ = [
    "apply_institutional_playbook_framework",
    "get_playbook",
    "health",
    "list_playbook_keys",
    "registry_summary",
    "resolve_playbook",
]
