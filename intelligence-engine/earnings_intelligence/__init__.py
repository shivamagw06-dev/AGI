"""P2.1 Financial Statements & Earnings Intelligence — NSE Master + IND-AS XBRL."""

from earnings_intelligence.production import analyse, attach_to_cid, health, package_for_ask_agi
from earnings_intelligence.schema import ENGINE_CODE, VERSION

__all__ = ["ENGINE_CODE", "VERSION", "analyse", "attach_to_cid", "health", "package_for_ask_agi"]
