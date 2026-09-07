"""HTML filing parser — lightweight label/value scrape; no invented numbers."""

from __future__ import annotations

import re
from typing import Any

from financial_statements_engine.parsing.schema import OUTPUT_SCHEMA, VERSION


class HtmlParser:
    parser_id = "html_filing_v1"
    version = "1.0.0"
    supported_formats = ("html",)
    supported_exchanges = ("NSE", "BSE", "ANY")
    supported_standards = ("IND_AS", "ANY")
    output_schema = OUTPUT_SCHEMA
    fallback_parser = None

    def can_parse(self, *, document_type: str, meta: dict[str, Any] | None = None) -> bool:
        return document_type.lower() == "html"

    def parse(self, data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        text = data.decode("utf-8", errors="replace")
        fields: dict[str, Any] = {}
        # Pattern: Label</td><td>123
        for m in re.finditer(
            r">([^<>]{3,80})</t[dh]>\s*<t[dh][^>]*>\s*([-+]?[0-9][0-9,]*(?:\.[0-9]+)?)",
            text,
            flags=re.I,
        ):
            label = re.sub(r"\s+", " ", m.group(1)).strip()
            try:
                val = float(m.group(2).replace(",", ""))
            except ValueError:
                continue
            fields[label] = {"value": val, "unit_scale": (meta or {}).get("unit_scale") or "crores"}
        return {
            "ok": True,
            "parser_id": self.parser_id,
            "parser_version": self.version,
            "pne_version": VERSION,
            "fields": fields,
            "periods": [],
            "sections": ["unknown"],
            "unknown_fields": [],
            "errors": [],
            "extraction_confidence": 0.6 if fields else 0.1,
        }
