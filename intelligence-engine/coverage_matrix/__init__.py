"""AGIB V1.5 — Coverage Matrix: operational view of *why* a company isn't yet ICC.

Boolean presence across evidence classes, kept separate from the clean
structured tables in `institutional_knowledge_tables`.
"""

from coverage_matrix.matrix import COVERAGE_MATRIX_VERSION, matrix_for_company, matrix_for_universe

__all__ = ["COVERAGE_MATRIX_VERSION", "matrix_for_company", "matrix_for_universe"]
