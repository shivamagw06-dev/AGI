"""Composite alpha placeholder — E03_COMPOSITE=false for P0/M0."""

from __future__ import annotations


def run_composite(*_args, **_kwargs):  # pragma: no cover
    raise RuntimeError("E03_COMPOSITE is disabled for P0/M0")
