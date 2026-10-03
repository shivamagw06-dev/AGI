"""Institutional Reasoning Pipeline (IRP) V1.

Sits ABOVE KIP and RSP and BELOW Ask AGI / UI Aggregation.
Architecture v1.0.1 LOCKED — no engine, KIP, or RSP redesign.

KIP retrieves. RSP reasons. IRP orchestrates institutional research thinking
before Ask AGI answers.
"""

from app.irp.flags import IrpFlags
from app.irp.service import IrpService

__all__ = ["IrpFlags", "IrpService"]
