"""AGI Forecasting & Learning Engine (FLE) v1.0.

Permanent forecast memory, outcome tracking, calibration and continuous learning.
Sits after IIE and before reasoning (KIP/IRP/RSP/Ask AGI).

Does not redesign KF1, KCV1, AOI, EVE, IIE, KIP, IRP, RSP, or Ask AGI.
"""

from app.fle.flags import FleFlags
from app.fle.service import FleService

__all__ = ["FleFlags", "FleService"]
