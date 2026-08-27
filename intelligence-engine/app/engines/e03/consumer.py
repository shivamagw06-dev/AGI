"""ORCH wiring — E03 passively consumes Feature Ready + E01/E14/E02 Ready."""

from __future__ import annotations

from typing import Any, Callable

from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e02.service import E02Service
from app.engines.e03.service import E03Service
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent

log = get_logger(__name__)


def register_e03_with_orch(
    l2: L2FeatureBuildService,
    e03: E03Service,
    e01: E01Service,
    e14: E14Service,
    e02: E02Service,
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
            e03.on_feature_ready(as_of=as_of, symbol=ready.symbol, snapshot=snapshot)
        except Exception as exc:
            log.warning("e03_feature_ready_failed", extra={"extra": {"error": str(exc)}})

    l2.on_ready(_on_ready)
    _wrap_e01(e01, e03)
    _wrap_e14(e14, e03)
    _wrap_e02(e02, e03)


def _wrap_e01(e01: E01Service, e03: E03Service) -> None:
    original = e01.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            e03.on_e01_ready(state)
        except Exception as exc:
            log.warning("e03_after_e01_failed", extra={"extra": {"error": str(exc)}})
        return state

    e01.run = _run  # type: ignore[method-assign]


def _wrap_e14(e14: E14Service, e03: E03Service) -> None:
    original = e14.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            e03.on_e14_ready(state)
        except Exception as exc:
            log.warning("e03_after_e14_failed", extra={"extra": {"error": str(exc)}})
        return state

    e14.run = _run  # type: ignore[method-assign]


def _wrap_e02(e02: E02Service, e03: E03Service) -> None:
    original = e02.run_universe

    def _run(*args: Any, **kwargs: Any):
        exposures = original(*args, **kwargs)
        try:
            e03.on_e02_ready(exposures)
        except Exception as exc:
            log.warning("e03_after_e02_failed", extra={"extra": {"error": str(exc)}})
        return exposures

    e02.run_universe = _run  # type: ignore[method-assign]
