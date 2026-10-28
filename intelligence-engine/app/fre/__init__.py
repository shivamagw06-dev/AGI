"""AGI Finance Retrieval Engine (FRE) v1.0.

Institutional intelligence acquisition layer — gathers, validates, structures,
indexes and serves public financial evidence to downstream AGIB engines.

FRE does NOT answer users. It returns ranked evidence with provenance.

Position (additive soft-wire):
  AOI / public sources → FRE → soft into CAE / KIP / Ask AGI

Does not redesign AOI, EVE, KF, KC, KIP, CAE, IRP, RSP, or Ask AGI.
Architecture: v1.0.1 LOCKED.
"""

from app.fre.flags import FreFlags
from app.fre.service import FreService

__all__ = ["FreFlags", "FreService"]
