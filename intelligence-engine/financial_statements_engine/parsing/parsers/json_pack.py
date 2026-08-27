"""JSON structured pack parser (fixtures / intermediate packs)."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.extraction.nse_xbrl import extract_from_earnings_pack
from financial_statements_engine.parsing.schema import OUTPUT_SCHEMA, VERSION


class JsonPackParser:
    parser_id = "json_pack_v1"
    version = "1.0.0"
    supported_formats = ("json",)
    supported_exchanges = ("ANY",)
    supported_standards = ("ANY",)
    output_schema = OUTPUT_SCHEMA
    fallback_parser = None

    def can_parse(self, *, document_type: str, meta: dict[str, Any] | None = None) -> bool:
        return document_type.lower() == "json"

    def parse(self, data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            pack = json.loads(data.decode("utf-8"))
        except Exception as exc:
            return {
                "ok": False,
                "parser_id": self.parser_id,
                "parser_version": self.version,
                "pne_version": VERSION,
                "fields": {},
                "periods": [],
                "sections": [],
                "unknown_fields": [],
                "errors": ["corrupt_document"],
                "error_detail": str(exc),
                "extraction_confidence": 0.0,
            }
        extracted = extract_from_earnings_pack(pack if isinstance(pack, dict) else {})
        periods = extracted.get("periods") or []
        fields = dict((periods[0] if periods else {}).get("fields") or {})
        # Also accept {"fields": {...}}
        if not fields and isinstance(pack, dict) and isinstance(pack.get("fields"), dict):
            fields = {
                k: (v if isinstance(v, dict) else {"value": v, "unit_scale": "crores"})
                for k, v in pack["fields"].items()
            }
        return {
            "ok": True,
            "parser_id": self.parser_id,
            "parser_version": self.version,
            "pne_version": VERSION,
            "fields": fields,
            "periods": periods,
            "sections": ["income_statement", "balance_sheet", "cash_flow"],
            "unknown_fields": [],
            "errors": [],
            "extraction_confidence": 0.95,
        }
