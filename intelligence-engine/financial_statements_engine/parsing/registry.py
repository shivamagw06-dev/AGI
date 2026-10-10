"""Parser registry — selection by document type / exchange / standard."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.parsers.csv_parser import CsvParser
from financial_statements_engine.parsing.parsers.excel import ExcelParser
from financial_statements_engine.parsing.parsers.html import HtmlParser
from financial_statements_engine.parsing.parsers.json_pack import JsonPackParser
from financial_statements_engine.parsing.parsers.pdf import PdfParser
from financial_statements_engine.parsing.parsers.xml_generic import XmlGenericParser
from financial_statements_engine.parsing.parsers.xbrl import XbrlParser
from financial_statements_engine.parsing.schema import OUTPUT_SCHEMA


def all_parsers() -> list[Any]:
    return [
        XbrlParser(),
        XmlGenericParser(),
        HtmlParser(),
        JsonPackParser(),
        PdfParser(),
        ExcelParser(),
        CsvParser(),
    ]


def select_parser(
    *,
    document_type: str,
    exchange: str | None = None,
    reporting_standard: str | None = None,
) -> Any | None:
    dt = (document_type or "unknown").lower()
    for parser in all_parsers():
        if not parser.can_parse(document_type=dt):
            continue
        if exchange and parser.supported_exchanges and exchange.upper() not in parser.supported_exchanges:
            # still allow if parser lists wildcard via empty — our parsers list specific exchanges
            if "ANY" not in parser.supported_exchanges:
                continue
        if reporting_standard and parser.supported_standards:
            if reporting_standard.upper() not in parser.supported_standards and "ANY" not in parser.supported_standards:
                continue
        return parser
    # Fallback: format-only match ignoring exchange/standard
    for parser in all_parsers():
        if parser.can_parse(document_type=dt):
            return parser
    return None


def registry_manifest() -> dict[str, Any]:
    rows = []
    for p in all_parsers():
        rows.append(
            {
                "parser_id": p.parser_id,
                "version": p.version,
                "supported_formats": list(p.supported_formats),
                "supported_exchanges": list(p.supported_exchanges),
                "supported_standards": list(p.supported_standards),
                "output_schema": getattr(p, "output_schema", OUTPUT_SCHEMA),
                "fallback_parser": p.fallback_parser,
            }
        )
    return {"parsers": rows, "n": len(rows)}
