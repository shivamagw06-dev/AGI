"""Shared helpers for connectors — no cross-connector imports of business logic."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.aoi.models import DocumentArtifact, ExtractedFact, SourceRef


def checksum_for(payload: str | bytes) -> str:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(data).hexdigest()


def make_artifact(
    *,
    connector_id: str,
    title: str,
    url: str,
    doc_type: str,
    company_id: str | None = None,
    fmt: str = "html",
    content: str = "",
    metadata: dict[str, Any] | None = None,
) -> DocumentArtifact:
    body = content or f"{title}\n{url}\n{doc_type}"
    return DocumentArtifact(
        connector_id=connector_id,
        company_id=company_id,
        title=title,
        url=url,
        doc_type=doc_type,
        format=fmt if fmt in {"pdf", "html", "xml", "json", "csv", "xlsx", "txt", "zip"} else "unknown",  # type: ignore[arg-type]
        checksum=checksum_for(body),
        size_bytes=len(body.encode("utf-8")),
        status="discovered",
        content_text=content,
        metadata=metadata or {},
    )


def fact(
    *,
    field: str,
    value_text: str,
    connector_id: str,
    source_name: str,
    document_id: str,
    company_id: str | None = None,
    confidence: float = 0.7,
    section: str | None = None,
    value: Any = None,
) -> ExtractedFact:
    return ExtractedFact(
        company_id=company_id,
        field=field,
        value=value if value is not None else value_text,
        value_text=value_text,
        source=SourceRef(connector_id=connector_id, source_name=source_name, url=""),
        document_id=document_id,
        section=section,
        confidence=confidence,
    )


def json_blob(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True)
