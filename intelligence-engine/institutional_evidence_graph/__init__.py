"""AGIB v3.6 Phase 2 — Institutional Evidence Graph (IEG)."""

from institutional_evidence_graph.assembler.engine import build_evidence_graph
from institutional_evidence_graph.schema import IEG_VERSION, MODULE_CODE, PROGRAMME

__all__ = [
    "IEG_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "build_evidence_graph",
]
