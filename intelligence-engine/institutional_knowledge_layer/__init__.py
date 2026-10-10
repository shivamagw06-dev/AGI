"""Institutional Knowledge Intelligence Layer (IKL).

Gather → Documents → Embeddings → Knowledge Extraction → Entity Memory →
Knowledge Graph → Ask AGI.

Façade over CID / Company Memory / KF / KC / KIL — never a second knowledge system.
"""

from institutional_knowledge_layer.production import (
    after_cgl_cycle,
    ask_consult,
    health,
    memory_snapshot,
    on_document,
    package_for_ask_agi,
)
from institutional_knowledge_layer.schema import (
    ASK_RETRIEVAL_ORDER,
    IKL_CODE,
    IKL_VERSION,
    PROGRAMME,
)

__all__ = [
    "ASK_RETRIEVAL_ORDER",
    "IKL_CODE",
    "IKL_VERSION",
    "PROGRAMME",
    "after_cgl_cycle",
    "ask_consult",
    "health",
    "memory_snapshot",
    "on_document",
    "package_for_ask_agi",
]
