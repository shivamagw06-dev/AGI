"""Placeholder — E08_GAMMA=false at P0. No gamma exposure model."""

from __future__ import annotations


def gamma_disabled() -> None:
    raise RuntimeError("E08_GAMMA is disabled at P0")
