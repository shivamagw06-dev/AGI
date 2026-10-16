"""Reasoning & Research Synthesis Platform (RSP) — institutional reasoning layer.

KIP retrieves. RSP reasons. LLM writes.
Architecture v1.0.1 locked. No engine redesign.
"""

from app.rsp.flags import RspFlags
from app.rsp.service import RspService

__all__ = ["RspFlags", "RspService"]
