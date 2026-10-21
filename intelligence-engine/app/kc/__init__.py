"""AGI Knowledge Corpus V1 (KCV1).

Populates and continuously improves the existing Knowledge Foundation.
Does not redesign Architecture / engines / KIP / KF / IRP / RSP.
"""

from app.kc.flags import KcFlags
from app.kc.service import KcService

__all__ = ["KcFlags", "KcService"]
