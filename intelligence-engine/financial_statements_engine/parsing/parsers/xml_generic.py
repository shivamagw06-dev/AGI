"""Generic XML fallback parser."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.parsers.xbrl import XbrlParser
from financial_statements_engine.parsing.schema import OUTPUT_SCHEMA


class XmlGenericParser(XbrlParser):
    parser_id = "xml_generic_v1"
    version = "1.0.0"
    supported_formats = ("xml",)
    supported_exchanges = ("ANY",)
    supported_standards = ("ANY",)
    output_schema = OUTPUT_SCHEMA
    fallback_parser = None

    def can_parse(self, *, document_type: str, meta: dict[str, Any] | None = None) -> bool:
        return document_type.lower() == "xml"
