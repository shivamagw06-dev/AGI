"""IRP service facade — Institutional Reasoning Pipeline V1."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.irp.flags import IrpFlags
from app.irp.learning import IrpLearningStore
from app.irp.models import IrpPackage
from app.irp.pipeline import IrpPipeline


class IrpService:
    """Orchestrates KIP retrieval + RSP reasoning for Ask AGI.

    Does not redesign engines, KIP, or RSP.
    """

    def __init__(
        self,
        *,
        kip: Any | None = None,
        rsp: Any | None = None,
        flags: IrpFlags | None = None,
        learning: IrpLearningStore | None = None,
    ) -> None:
        self.flags = flags or IrpFlags.from_settings(get_settings())
        self.kip = kip
        self.rsp = rsp
        self.learning = learning or IrpLearningStore()
        self.pipeline = IrpPipeline(kip=kip, rsp=rsp, learning=self.learning)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.irp else "disabled",
            "layer": "Institutional Reasoning Pipeline",
            "programme": "IRP V1",
            "version": "irp-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "above_kip_rsp_below_ask_agi",
            "flags": self.flags.as_dict(),
            "learning_records": len(self.learning.recent(500)),
        }

    def run(self, question: str, *, ticker: str | None = None) -> IrpPackage:
        self._require()
        return self.pipeline.run(question, ticker=ticker)

    def recent_learning(self, limit: int = 20) -> list[dict[str, Any]]:
        self._require()
        return self.learning.recent(limit=limit)

    def _require(self) -> None:
        if not self.flags.irp:
            raise RuntimeError("IRP is disabled (IRP=false)")
