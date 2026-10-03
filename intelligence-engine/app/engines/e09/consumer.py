"""ORCH wiring — E09 passively consumes Feature Ready + E01 Ready + E14 Ready."""

from __future__ import annotations

from typing import Any, Callable

from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e09.service import E09Service
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent

log = get_logger(__name__)


def register_e09_with_orch(
    l2: L2FeatureBuildService,
    e09: E09Service,
    e01: E01Service,
    e14: E14Service,
    *,
    snapshot_provider: Callable[[FeatureReadyEvent], FeatureSnapshot | None] | None = None,
) -> None:
    def _on_ready(ready: FeatureReadyEvent) -> None:
        as_of = str(ready.as_of)[:10]
        snapshot: FeatureSnapshot | None = None
        if snapshot_provider is not None:
            snapshot = snapshot_provider(ready)
        elif ready.snapshot_id:
            snapshot = l2._last_snapshots.get(ready.snapshot_id)
        try:
            e09.on_feature_ready(as_of=as_of, symbol=ready.symbol, snapshot=snapshot)
        except Exception as exc:
            log.warning("e09_feature_ready_failed", extra={"extra": {"error": str(exc)}})

    l2.on_ready(_on_ready)
    _wrap_e01(e01, e09)
    _wrap_e14(e14, e09)


def _wrap_e01(e01: E01Service, e09: E09Service) -> None:
    original = e01.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            e09.on_e01_ready(state)
        except Exception as exc:
            log.warning("e09_after_e01_failed", extra={"extra": {"error": str(exc)}})
        return state

    e01.run = _run  # type: ignore[method-assign]


def _wrap_e14(e14: E14Service, e09: E09Service) -> None:
    original = e14.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            e09.on_e14_ready(state)
        except Exception as exc:
            log.warning("e09_after_e14_failed", extra={"extra": {"error": str(exc)}})
        return state

    e14.run = _run  # type: ignore[method-assign]
