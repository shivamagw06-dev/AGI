"""Assertion Compiler — KPE sub-component (extract + validate).

Converts normalized evidence into institutional assertions.
Part of Knowledge Production Engine; not a separate architecture layer.
"""

from __future__ import annotations

from typing import Any

from institutional_knowledge_factory.extract import extract_claims
from institutional_knowledge_factory.validate import validate_evidence_batch


def compile_assertions(
    normalized_sources: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract claims from sources and validate. Returns (valid_claims, extracted, reports)."""
    extracted = extract_claims(normalized_sources)
    valid_claims, validation_reports = validate_evidence_batch(extracted)
    return valid_claims, extracted, validation_reports
