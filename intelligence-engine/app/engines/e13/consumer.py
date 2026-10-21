"""ORCH wiring — E13 passively consumes Feature Ready + E01 Ready + E14 Ready."""

from __future__ import annotations

from typing import Any, Callable

from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e13.service import E13Service
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent

log = get_logger(__name__)


def register_e13_with_orch(
    l2: L2FeatureBuildService,
    e13: E13Service,
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
            e13.on_feature_ready(as_of=as_of, symbol=ready.symbol, snapshot=snapshot)
        except Exception as exc:
            log.warning("e13_feature_ready_failed", extra={"extra": {"error": str(exc)}})

    l2.on_ready(_on_ready)
    _wrap_e01(e01, e13)
    _wrap_e14(e14, e13)


def _wrap_e01(e01: E01Service, e13: E13Service) -> None:
    original = e01.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            e13.on_e01_ready(state)
        except Exception as exc:
            log.warning("e13_after_e01_failed", extra={"extra": {"error": str(exc)}})
        return state

    e01.run = _run  # type: ignore[method-assign]


def _wrap_e14(e14: E14Service, e13: E13Service) -> None:
    original = e14.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            e13.on_e14_ready(state)
        except Exception as exc:
            log.warning("e13_after_e14_failed", extra={"extra": {"error": str(exc)}})
        return state

    e14.run = _run  # type: ignore[method-assign]
