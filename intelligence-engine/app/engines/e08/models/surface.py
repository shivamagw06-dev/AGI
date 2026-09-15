"""Placeholder — E08_SURFACE=false at P0. No options surface modelling."""

from __future__ import annotations


def surface_disabled() -> None:
    raise RuntimeError("E08_SURFACE is disabled at P0")
