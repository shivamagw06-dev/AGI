"""Production façades for the Coverage Matrix."""

from __future__ import annotations

from typing import Any

from coverage_matrix.matrix import COVERAGE_MATRIX_VERSION, matrix_for_company, matrix_for_universe


def health() -> dict[str, Any]:
    return {"ok": True, "version": COVERAGE_MATRIX_VERSION}


__all__ = ["health", "matrix_for_company", "matrix_for_universe"]
