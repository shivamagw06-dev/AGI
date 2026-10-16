"""ML / ensemble placeholder — L4_ML=false for P0 Shadow."""

from __future__ import annotations


def fuse_ml(*_args, **_kwargs):  # pragma: no cover
    raise RuntimeError("L4_ML is disabled for P0 Shadow")
