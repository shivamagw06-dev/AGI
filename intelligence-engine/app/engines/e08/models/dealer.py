"""Placeholder — E08_DEALER=false at P0. No dealer positioning."""

from __future__ import annotations


def dealer_disabled() -> None:
    raise RuntimeError("E08_DEALER is disabled at P0")
