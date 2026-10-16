"""AGIB v3.4 Track C — Institutional Framework Selection Engine (IFSE)."""

from framework_selection.schema import IFSE_VERSION, MODULE_CODE, PROGRAMME
from framework_selection.selector.engine import select_frameworks

__all__ = [
    "IFSE_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "select_frameworks",
]
