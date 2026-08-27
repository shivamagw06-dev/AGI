"""ORCH wiring — E10 passively rebuilds after L4 Ready."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.engines.e10.service import E10Service
from app.engines.l4.service import L4Service

log = get_logger(__name__)


def register_e10_with_orch(e10: E10Service, l4: L4Service) -> None:
    """Trigger E10 only from L4 completion. No polling / scheduling."""
    _wrap_l4_run(l4, e10)
    _wrap_l4_batch(l4, e10)


def _wrap_l4_run(l4: L4Service, e10: E10Service) -> None:
    original = l4.run

    def _run(*args: Any, **kwargs: Any):
        opinion = original(*args, **kwargs)
        try:
            e10.on_l4_ready(opinion)
        except Exception as exc:
            log.warning("e10_after_l4_run_failed", extra={"extra": {"error": str(exc)}})
        return opinion

    l4.run = _run  # type: ignore[method-assign]


def _wrap_l4_batch(l4: L4Service, e10: E10Service) -> None:
    original = l4.run_symbols

    def _run(*args: Any, **kwargs: Any):
        opinions = original(*args, **kwargs)
        try:
            e10.on_l4_ready(opinions)
        except Exception as exc:
            log.warning("e10_after_l4_batch_failed", extra={"extra": {"error": str(exc)}})
        return opinions

    l4.run_symbols = _run  # type: ignore[method-assign]
