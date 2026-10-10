"""IDI validators — provenance, checksum, duplicates, future leakage."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.schema import DOCUMENT_TYPES, OFFICIAL_SOURCES

VALIDATOR_ID = "idi_validator_v1"


def validate_document(doc: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    if not doc.get("document_id"):
        failures.append("missing_document_id")
    if not doc.get("company"):
        failures.append("missing_company")
    if doc.get("type") not in DOCUMENT_TYPES:
        failures.append("unknown_document_type")
    if doc.get("source") not in OFFICIAL_SOURCES:
        failures.append("unknown_source")
    if doc.get("fabricated") is True:
        failures.append("fabricated_document")
    if not doc.get("text"):
        failures.append("missing_body")
    if not doc.get("checksum") and doc.get("text"):
        failures.append("missing_checksum")
    if doc.get("text") and doc.get("checksum"):
        if store.checksum_text(doc["text"]) != doc["checksum"]:
            failures.append("checksum_mismatch")
    if not doc.get("provenance"):
        failures.append("missing_provenance")
    else:
        prov = doc["provenance"]
        for k in ("official_source", "collector", "retrieved_at"):
            if not prov.get(k):
                failures.append(f"provenance_missing:{k}")

    for dkey in ("published_date", "available_from"):
        val = doc.get(dkey)
        if not val:
            failures.append(f"missing_{dkey}")
        else:
            try:
                datetime.fromisoformat(str(val)[:10])
            except Exception:
                failures.append(f"invalid_{dkey}")

    # Future leakage: available_from must not be after as_of when as_of provided
    if as_of and doc.get("available_from"):
        if str(doc["available_from"])[:10] > str(as_of)[:10]:
            failures.append("future_leakage")

    # Duplicate detection against store
    existing = store.get_document(str(doc.get("document_id") or ""))
    if existing and existing.get("checksum") and doc.get("checksum"):
        if existing["checksum"] != doc["checksum"] and existing.get("version") == doc.get("version"):
            failures.append("duplicate_conflict")

    # Same company+type+published+checksum already present under different id
    for other in store.list_documents(ticker=doc.get("company")):
        if other.get("document_id") == doc.get("document_id"):
            continue
        if (
            other.get("type") == doc.get("type")
            and other.get("published_date") == doc.get("published_date")
            and other.get("checksum")
            and other.get("checksum") == doc.get("checksum")
        ):
            failures.append("duplicate_document")

    ok = not failures
    verdict = {
        "ok": ok,
        "validator": VALIDATOR_ID,
        "failures": sorted(set(failures)),
        "warnings": warnings,
        "validated_at": store.utc_now(),
    }
    store.log_validation(
        {
            "document_id": doc.get("document_id"),
            "company": doc.get("company"),
            "ok": ok,
            "failures": verdict["failures"],
        }
    )
    return verdict
