"""CSV parser stub — quarantine (structured CSV support later)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.schema import OUTPUT_SCHEMA, VERSION


class CsvParser:
    parser_id = "csv_stub_v1"
    version = "0.0.1"
    supported_formats = ("csv",)
    supported_exchanges = ("ANY",)
    supported_standards = ("ANY",)
    output_schema = OUTPUT_SCHEMA
    fallback_parser = None

    def can_parse(self, *, document_type: str, meta: dict[str, Any] | None = None) -> bool:
        return document_type.lower() == "csv"

    def parse(self, data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "quarantine": True,
            "parser_id": self.parser_id,
            "parser_version": self.version,
            "pne_version": VERSION,
            "fields": {},
            "periods": [],
            "sections": [],
            "unknown_fields": [],
            "errors": ["unsupported_format"],
            "error_detail": "csv_parser_not_implemented",
            "extraction_confidence": 0.0,
        }
