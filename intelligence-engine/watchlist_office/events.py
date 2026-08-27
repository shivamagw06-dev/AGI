"""PEB-01 subscriptions — first event-driven office workflow."""

from __future__ import annotations

from threading import Lock
from typing import Any

from watchlist_office.service import apply_event_to_entries

_LOCK = Lock()
_WIRED = False
SUBSCRIBER_ID = "wo-01-research-queue"


def _handler(event: dict[str, Any]) -> None:
    apply_event_to_entries(event)


def ensure_subscriptions() -> dict[str, Any]:
    """Idempotently subscribe WO-01 to research lifecycle events."""
    global _WIRED
    with _LOCK:
        if _WIRED:
            return {"ok": True, "already_wired": True, "subscriber_id": SUBSCRIBER_ID}
        try:
            from platform_event_bus.subscriber import subscribe
            from platform_event_bus.schema import (
                EVENT_BUSINESS_QUALITY_UPDATED,
                EVENT_COMPANY_RESEARCH_COMPLETED,
                EVENT_COMPARISON_COMPLETED,
                EVENT_MANAGEMENT_EXECUTION_UPDATED,
            )

            patterns = [
                EVENT_COMPANY_RESEARCH_COMPLETED,
                EVENT_COMPARISON_COMPLETED,
                EVENT_BUSINESS_QUALITY_UPDATED,
                EVENT_MANAGEMENT_EXECUTION_UPDATED,
            ]
            sid = subscribe(patterns, _handler, subscriber_id=SUBSCRIBER_ID, name="WO-01 Research Queue")
            _WIRED = True
            return {"ok": True, "already_wired": False, "subscriber_id": sid, "patterns": patterns}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def reset_subscriptions_for_tests() -> None:
    global _WIRED
    with _LOCK:
        _WIRED = False
        try:
            from platform_event_bus.dispatcher import get_dispatcher

            get_dispatcher().unsubscribe(SUBSCRIBER_ID)
        except Exception:
            pass
