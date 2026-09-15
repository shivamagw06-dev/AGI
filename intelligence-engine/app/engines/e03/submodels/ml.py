"""ML placeholder — E03_ML=false for P0/M0."""

from __future__ import annotations


def run_ml(*_args, **_kwargs):  # pragma: no cover
    raise RuntimeError("E03_ML is disabled for P0/M0")
