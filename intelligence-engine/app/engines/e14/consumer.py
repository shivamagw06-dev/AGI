"""ORCH wiring — E14 passively consumes FeatureSnapshot + E01State."""

from __future__ import annotations

from typing import Any, Callable

from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent

log = get_logger(__name__)


def register_e14_with_orch(
    l2: L2FeatureBuildService,
    e14: E14Service,
    e01: E01Service,
    *,
    snapshot_provider: Callable[[FeatureReadyEvent], FeatureSnapshot | None] | None = None,
) -> None:
    """
    Register E14 on L2 ready events. Loads E01State from E01 cache (no polling).
    """

    def _on_ready(ready: FeatureReadyEvent) -> None:
        as_of = str(ready.as_of)[:10]
        snapshot: FeatureSnapshot | None = None
        if snapshot_provider is not None:
            snapshot = snapshot_provider(ready)
        elif ready.snapshot_id:
            snapshot = l2._last_snapshots.get(ready.snapshot_id)
        e01_state = e01.get_state(as_of=as_of) or e01.get_state()
        # Run when macro/vol features ready or when E01 already available
        feature_ids = set(ready.feature_ids or [])
        relevant = any(
            fid.startswith(("MACRO_", "VOL_", "TECH_")) for fid in feature_ids
        ) or e01_state is not None
        if not relevant and snapshot is None:
            return
        try:
            e14.on_inputs_ready(as_of=as_of, snapshot=snapshot, e01_state=e01_state)
        except Exception as exc:
            log.warning("e14_ready_consume_failed", extra={"extra": {"error": str(exc)}})

    l2.on_ready(_on_ready)

    # Also re-run E14 whenever E01 produces a new state via a thin wrapper hook
    _wrap_e01_run(e01, e14)


def _wrap_e01_run(e01: E01Service, e14: E14Service) -> None:
    """After E01.run succeeds, refresh firm E14 prior (passive chain, not polling)."""
    original = e01.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            as_of = state.as_of
            e14.on_inputs_ready(as_of=as_of, e01_state=state)
        except Exception as exc:
            log.warning("e14_after_e01_failed", extra={"extra": {"error": str(exc)}})
        return state

    e01.run = _run  # type: ignore[method-assign]
