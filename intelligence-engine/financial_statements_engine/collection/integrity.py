"""Integrity Verifier — size, hash, completeness (FSE-02 §6.4)."""

from __future__ import annotations

import hashlib
from typing import Any


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_download(
    data: bytes,
    *,
    expected_sha256: str | None = None,
    min_bytes: int = 1,
    document_type: str | None = None,
) -> dict[str, Any]:
    """Verify download completeness. Never modifies bytes."""
    issues: list[str] = []
    size = len(data) if data is not None else 0
    if data is None or size < min_bytes:
        issues.append("empty_or_incomplete")
    digest = sha256_hex(data or b"")
    if expected_sha256 and expected_sha256.removeprefix("sha256:") != digest:
        issues.append("checksum_mismatch")

    # Light content-type sanity (not a parser)
    head = (data or b"")[:200].lstrip()
    dt = (document_type or "").lower()
    if dt == "xbrl" and head and not (head.startswith(b"<") or head.startswith(b"{")):
        issues.append("xbrl_content_sanity")
    if dt == "pdf" and head and not head.startswith(b"%PDF"):
        issues.append("pdf_content_sanity")

    ok = not issues
    return {
        "ok": ok,
        "size_bytes": size,
        "content_sha256": digest,
        "evidence_id": f"sha256:{digest}",
        "issues": issues,
        "layer": "integrity_verifier",
    }
