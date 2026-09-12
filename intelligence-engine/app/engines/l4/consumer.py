"""ORCH wiring — L4 passively consumes E01/E14/E02/E03 Ready (shadow only)."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e02.service import E02Service
from app.engines.e03.service import E03Service
from app.engines.e14.service import E14Service
from app.engines.l4.service import L4Service

log = get_logger(__name__)


def register_l4_with_orch(
    l4: L4Service,
    e01: E01Service,
    e14: E14Service,
    e02: E02Service,
    e03: E03Service,
) -> None:
    """Register L4 as passive after-hook. Does not touch FeatureSnapshot / MarketData."""
    _wrap_e01(e01, l4)
    _wrap_e14(e14, l4)
    _wrap_e02(e02, l4)
    _wrap_e03(e03, l4)


def _wrap_e01(e01: E01Service, l4: L4Service) -> None:
    original = e01.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            l4.on_e01_ready(state)
        except Exception as exc:
            log.warning("l4_after_e01_failed", extra={"extra": {"error": str(exc)}})
        return state

    e01.run = _run  # type: ignore[method-assign]


def _wrap_e14(e14: E14Service, l4: L4Service) -> None:
    original = e14.run

    def _run(*args: Any, **kwargs: Any):
        state = original(*args, **kwargs)
        try:
            l4.on_e14_ready(state)
        except Exception as exc:
            log.warning("l4_after_e14_failed", extra={"extra": {"error": str(exc)}})
        return state

    e14.run = _run  # type: ignore[method-assign]


def _wrap_e02(e02: E02Service, l4: L4Service) -> None:
    original = e02.run_universe

    def _run(*args: Any, **kwargs: Any):
        exposures = original(*args, **kwargs)
        try:
            l4.on_e02_ready(exposures)
        except Exception as exc:
            log.warning("l4_after_e02_failed", extra={"extra": {"error": str(exc)}})
        return exposures

    e02.run_universe = _run  # type: ignore[method-assign]


def _wrap_e03(e03: E03Service, l4: L4Service) -> None:
    original = e03.run_universe

    def _run(*args: Any, **kwargs: Any):
        alphas = original(*args, **kwargs)
        try:
            l4.on_e03_ready(alphas)
        except Exception as exc:
            log.warning("l4_after_e03_failed", extra={"extra": {"error": str(exc)}})
        return alphas

    e03.run_universe = _run  # type: ignore[method-assign]
