"""Institutional Analytical Playbook registry."""

from institutional_playbooks.registry.index import (
    category_counts,
    get_playbook,
    list_playbooks,
    playbook_ids,
    registry_index,
)

__all__ = [
    "category_counts",
    "get_playbook",
    "list_playbooks",
    "playbook_ids",
    "registry_index",
]
