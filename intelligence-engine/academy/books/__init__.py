"""AGI Academy Books — structured institutional learning from curated books.

Architecture v1.0.1 LOCKED. Not an engine, not an LLM, not a recommender.
Converts books into AGI-owned knowledge objects (concepts / frameworks / formulas).
Never stores searchable PDFs or long verbatim copyrighted text.
"""

from academy.books.flags import is_books_enabled
from academy.books.production import dashboard, package_for_query, quality_gates
from academy.books.schema import BOOKS_VERSION

__all__ = [
    "BOOKS_VERSION",
    "dashboard",
    "is_books_enabled",
    "package_for_query",
    "quality_gates",
]
