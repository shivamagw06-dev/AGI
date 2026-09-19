"""AGI Market Event Engine (MEE) v1.0.

Canonical event detection, impact propagation and market timelines.
Sits after FLE and before reasoning / future PMO·IME·AMS.

Does not redesign KF1, KCV1, AOI, EVE, IIE, FLE, KIP, IRP, RSP, or Ask AGI.
"""

from app.mee.flags import MeeFlags
from app.mee.service import MeeService

__all__ = ["MeeFlags", "MeeService"]
