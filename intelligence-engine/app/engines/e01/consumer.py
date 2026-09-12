"""ORCH L2 → E01 wiring: E01 is a passive FeatureSnapshot consumer."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.features.models import FeatureSnapshot
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent

log = get_logger(__name__)


def register_e01_with_orch_l2(
    l2: L2FeatureBuildService,
    e01: E01Service,
    *,
    snapshot_provider: Any | None = None,
) -> None:
    """
    Register E01 on L2 ready events. No polling. No market-data access.

    snapshot_provider(ready) -> FeatureSnapshot | None optional hook for tests.
    """

    def _on_ready(ready: FeatureReadyEvent) -> None:
        snapshot: FeatureSnapshot | None = None
        if snapshot_provider is not None:
            snapshot = snapshot_provider(ready)
        elif ready.snapshot_id and getattr(l2, "_last_snapshots", None):
            snapshot = l2._last_snapshots.get(ready.snapshot_id)  # type: ignore[attr-defined]
        try:
            e01.on_feature_ready(ready, snapshot=snapshot)
        except Exception as exc:
            log.warning("e01_ready_consume_failed", extra={"extra": {"error": str(exc)}})

    l2.on_ready(_on_ready)
