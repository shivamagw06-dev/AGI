"""AGI Investment Intelligence Engine (IIE) v1.0.

Transforms verified EVE evidence into reusable institutional investment intelligence.
Sits after EVE / KCV / KF and before reasoning (KIP/IRP/RSP/Ask AGI).

Does not redesign KF1, KCV1, AOI, EVE, KIP, IRP, RSP, or Ask AGI.
"""

from app.iie.flags import IieFlags
from app.iie.service import IieService

__all__ = ["IieFlags", "IieService"]
