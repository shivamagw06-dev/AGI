"""Management Intelligence Engine V1 — can management be trusted?"""

from management_intelligence.production import analyse, company, dashboard, guidance, history, quality_gates
from management_intelligence.schema import MII_VERSION

__all__ = [
    "MII_VERSION",
    "analyse",
    "company",
    "dashboard",
    "guidance",
    "history",
    "quality_gates",
]
