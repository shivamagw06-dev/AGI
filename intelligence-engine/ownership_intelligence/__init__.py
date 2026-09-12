"""P2.3 Ownership Intelligence — NSE Master + XBRL evidence layer."""

from ownership_intelligence.production import analyse, attach_to_cid, health, package_for_ask_agi
from ownership_intelligence.schema import ENGINE_CODE, VERSION

__all__ = [
    "ENGINE_CODE",
    "VERSION",
    "analyse",
    "attach_to_cid",
    "health",
    "package_for_ask_agi",
]
