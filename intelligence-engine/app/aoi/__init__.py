"""AGI Open Intelligence (AOI) v1.0 — autonomous public knowledge acquisition.

Acquires, validates and maintains institutional knowledge from public sources.
Soft-publishes into Knowledge Corpus / Knowledge Foundation.

Does not redesign KF1, KCV1, KIP, IRP, RSP, Ask AGI, or locked Architecture v1.0.1.
"""

from app.aoi.flags import AoiFlags
from app.aoi.service import AoiService

__all__ = ["AoiFlags", "AoiService"]
