"""Knowledge Foundation V1 (KF1).

Builds structured institutional investment knowledge objects that power
the existing Architecture v1.0.1 stack.

Reads from KIP. Does not redesign KIP, IRP, RSP, or engines.
"""

from app.kf.flags import KfFlags
from app.kf.service import KfService

__all__ = ["KfFlags", "KfService"]
