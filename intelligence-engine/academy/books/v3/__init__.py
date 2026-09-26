"""Academy Books V3 — institutional knowledge transformation (no engine redesign)."""

from academy.books.v3.production import (
    analyst_base,
    bootstrap,
    dashboard,
    package_for_query,
    quality_gates,
    reset_for_tests,
    soft_slice_for_package,
)
from academy.books.v3.retrieval import institutional_ask, knowledge_for_analyst
from academy.books.v3.schema import BOOKS_V3_VERSION

__all__ = [
    "BOOKS_V3_VERSION",
    "analyst_base",
    "bootstrap",
    "dashboard",
    "institutional_ask",
    "knowledge_for_analyst",
    "package_for_query",
    "quality_gates",
    "reset_for_tests",
    "soft_slice_for_package",
]
