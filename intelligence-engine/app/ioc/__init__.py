"""Investment Operations Centre (IOC) — mission control for the AGI Investment Office.

Monitors platforms only. Creates no investment opinions or research.
Architecture v1.0.1 locked. No engine redesign.
"""

from app.ioc.flags import IocFlags
from app.ioc.service import IocService

__all__ = ["IocFlags", "IocService"]
