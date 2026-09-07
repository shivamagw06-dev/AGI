"""Knowledge Intelligence Platform (KIP) — institutional memory layer for AGI.

Architecture v1.0.1 locked. Does not redesign research engines.
LLM never learns by changing weights; knowledge is extracted, indexed, linked.
"""

from app.kip.flags import KipFlags
from app.kip.service import KipService

__all__ = ["KipFlags", "KipService"]
