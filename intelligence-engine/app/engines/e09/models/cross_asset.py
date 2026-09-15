"""Placeholder — E09_CROSS_ASSET=false at P0. No cross-asset execution."""

from __future__ import annotations


def cross_asset_disabled() -> None:
    raise RuntimeError("E09_CROSS_ASSET is disabled at P0")
