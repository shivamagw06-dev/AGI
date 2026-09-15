"""AGI Context Assembly Engine (CAE) v1.0.

Unified intelligence orchestration — assembles one institutional context package
before reasoning. Does not replace or redesign KF1, KCV1, AOI, EVE, IIE, FLE, MEE,
KIP, IRP, RSP, or Ask AGI.
"""

from app.cae.flags import CaeFlags
from app.cae.service import CaeService

__all__ = ["CaeFlags", "CaeService"]
