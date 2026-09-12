"""Office SDK — shared contracts for AGIB application offices."""

from office_sdk.contracts import (
    confidence_summary,
    evidence_block,
    evidence_reference,
    office_metadata,
    office_request,
    office_response,
    provenance_bundle,
)
from office_sdk.registry import catalog, dispatch
from office_sdk.schema import SDK_VERSION, SDK_WORKSTREAM_ID

__all__ = [
    "SDK_VERSION",
    "SDK_WORKSTREAM_ID",
    "evidence_block",
    "evidence_reference",
    "confidence_summary",
    "provenance_bundle",
    "office_metadata",
    "office_request",
    "office_response",
    "catalog",
    "dispatch",
]
