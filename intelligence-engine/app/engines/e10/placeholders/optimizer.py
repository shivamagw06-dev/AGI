"""Generic optimiser placeholder — E10_OPTIMIZER=false for P0."""

from __future__ import annotations


def optimise(*_args, **_kwargs):  # pragma: no cover
    raise RuntimeError("E10_OPTIMIZER is disabled for P0")
