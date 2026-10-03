"""Module 7 — Evidence Validation.

This is the single hard gate all of Modules 1-6 must pass through before
anything reaches the Knowledge Store. Facts without evidence never enter the
knowledge base — this module is imported directly by storage/base.py and
called on every ``store_fact`` / ``store_paragraph`` call, so no code path can
bypass it.
"""

from __future__ import annotations

from typing import Any

from kip_v2.schema import Evidence, Fact

REQUIRED_FACT_FIELDS = ("fact_id", "company_id", "category", "key", "confidence", "evidence", "source_document_id")


def validate_evidence(evidence: Evidence | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if evidence is None:
        return False, ["evidence.missing"]
    if not evidence.document_id:
        errors.append("evidence.document_id.missing")
    if not evidence.paragraph_id:
        errors.append("evidence.paragraph_id.missing")
    if not isinstance(evidence.page, int) or evidence.page < 1:
        errors.append("evidence.page.invalid")
    snippet = (evidence.snippet or "").strip()
    if len(snippet) < 8:
        errors.append("evidence.snippet.too_short")
    if not evidence.evidence_hash:
        errors.append("evidence.hash.missing")
    elif not evidence.is_hash_consistent():
        errors.append("evidence.hash.mismatch")
    return (len(errors) == 0, errors)


def validate_fact(fact: Fact) -> tuple[bool, list[str]]:
    """The Module 7 gate. Returns (is_valid, errors). A fact is valid only if
    every quality-contract field is present AND the evidence itself is valid.
    """

    errors: list[str] = []
    for field_name in REQUIRED_FACT_FIELDS:
        if getattr(fact, field_name, None) in (None, ""):
            errors.append(f"fact.{field_name}.missing")

    if not (0.0 <= float(fact.confidence or 0.0) <= 1.0):
        errors.append("fact.confidence.out_of_range")

    ev_ok, ev_errors = validate_evidence(fact.evidence)
    if not ev_ok:
        errors.extend(ev_errors)

    if fact.evidence is not None and fact.evidence.document_id != fact.source_document_id:
        errors.append("fact.source_document_id.mismatch")

    return (len(errors) == 0, errors)


def quality_contract_fields(fact_dict: dict[str, Any]) -> tuple[bool, list[str]]:
    """Checks the QUALITY CONTRACT list literally: evidence, page, confidence,
    timestamp, source, version must all be present on a stored fact dict."""

    required = ("evidence", "confidence", "timestamp", "source_document_id", "version")
    missing = [f for f in required if fact_dict.get(f) in (None, "")]
    if "evidence" in fact_dict and isinstance(fact_dict.get("evidence"), dict):
        if not fact_dict["evidence"].get("page"):
            missing.append("evidence.page")
    return (len(missing) == 0, missing)
