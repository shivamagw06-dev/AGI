"""AGI Evidence & Verification Engine (EVE) v1.0.

Sits between AOI and KCV/KF — provenance, trust, conflicts, timelines.
Does not redesign KF1, KCV1, AOI, KIP, IRP, RSP, or Ask AGI.
"""

from app.eve.flags import EveFlags
from app.eve.service import EveService

__all__ = ["EveFlags", "EveService"]
