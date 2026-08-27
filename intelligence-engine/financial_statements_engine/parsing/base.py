"""Common parser interface — every format parser implements this."""

from __future__ import annotations

from typing import Any, Protocol


class DocumentParser(Protocol):
    parser_id: str
    version: str
    supported_formats: tuple[str, ...]
    supported_exchanges: tuple[str, ...]
    supported_standards: tuple[str, ...]
    output_schema: str
    fallback_parser: str | None

    def can_parse(self, *, document_type: str, meta: dict[str, Any] | None = None) -> bool: ...

    def parse(self, data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return extraction result: fields, sections, unknown_fields, errors, confidence.

        Must not invent values. Must not normalize via private synonym tables.
        """
        ...
