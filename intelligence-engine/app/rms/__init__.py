"""Research Management System (RMS) — institutional research workflow platform.

Idea → Request → Knowledge → RSP → Draft → Review → Approve → Publish → KIP.
Architecture v1.0.1 locked. No engine/CMS redesign.
"""

from app.rms.flags import RmsFlags
from app.rms.service import RmsService

__all__ = ["RmsFlags", "RmsService"]
