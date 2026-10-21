"""AGIB Governance Specification — constitutional rules for Phase 6+.

Constitution → Governance Specification → Test Runner → Evaluation Results
"""

from governance_spec.phase6 import format_board, run_phase6
from governance_spec.registry import list_specs, load_spec
from governance_spec.schema import GOVERNANCE_SPEC_VERSION
from governance_spec.v1_0.rules import spec_board

__all__ = [
    "GOVERNANCE_SPEC_VERSION",
    "load_spec",
    "list_specs",
    "spec_board",
    "run_phase6",
    "format_board",
]
