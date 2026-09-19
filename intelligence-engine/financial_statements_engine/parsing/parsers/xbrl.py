"""XBRL / iXBRL parser — structured extraction; no private synonym maps."""

from __future__ import annotations

import json
import re
from typing import Any
from xml.etree import ElementTree as ET

from financial_statements_engine.parsing.schema import OUTPUT_SCHEMA, VERSION


class XbrlParser:
    parser_id = "nse_indas_xbrl_v1"
    version = "1.0.0"
    supported_formats = ("xbrl", "ixbrl", "xml")
    supported_exchanges = ("NSE", "BSE", "ANY")
    supported_standards = ("IND_AS", "IFRS", "ANY")
    output_schema = OUTPUT_SCHEMA
    fallback_parser = "xml_generic_v1"

    def can_parse(self, *, document_type: str, meta: dict[str, Any] | None = None) -> bool:
        return document_type.lower() in self.supported_formats

    def parse(self, data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        meta = meta or {}
        text = data.decode("utf-8", errors="replace")
        # JSON fixture wrapped as xbrl-compatible structured pack
        if text.lstrip().startswith("{"):
            try:
                pack = json.loads(text)
                from financial_statements_engine.extraction.nse_xbrl import extract_from_earnings_pack

                extracted = extract_from_earnings_pack(pack)
                periods = extracted.get("periods") or []
                fields: dict[str, Any] = {}
                if periods:
                    fields = dict(periods[0].get("fields") or {})
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
                    "extraction_confidence": float((periods[0] if periods else {}).get("confidence") or 0.9),
                }
            except Exception as exc:
                return self._fail(str(exc), "parse_failure")

        # Lightweight XBRL/XML tag scrape (deterministic; no invented values)
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            # regex fallback for simple fixtures
            return self._regex_extract(text)

        fields: dict[str, Any] = {}
        for el in root.iter():
            tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
            if not tag or el.text is None:
                continue
            raw = el.text.strip()
            if raw == "":
                fields[tag] = {"value": None, "unit_scale": meta.get("unit_scale") or "crores"}
                continue
            try:
                num = float(raw.replace(",", ""))
            except ValueError:
                continue
            fields[tag] = {"value": num, "unit_scale": meta.get("unit_scale") or "crores"}

        return {
            "ok": True,
            "parser_id": self.parser_id,
            "parser_version": self.version,
            "pne_version": VERSION,
            "fields": fields,
            "periods": [],
            "sections": self._detect_sections(fields),
            "unknown_fields": [],
            "errors": [],
            "extraction_confidence": 0.85 if fields else 0.2,
        }

    def _regex_extract(self, text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for m in re.finditer(r"<([A-Za-z0-9_]+)>([^<]*)</\1>", text):
            tag, raw = m.group(1), m.group(2).strip()
            if raw == "":
                fields[tag] = {"value": None, "unit_scale": "crores"}
                continue
            try:
                fields[tag] = {"value": float(raw.replace(",", "")), "unit_scale": "crores"}
            except ValueError:
                continue
        return {
            "ok": bool(fields),
            "parser_id": self.parser_id,
            "parser_version": self.version,
            "pne_version": VERSION,
            "fields": fields,
            "periods": [],
            "sections": self._detect_sections(fields),
            "unknown_fields": [],
            "errors": [] if fields else ["parse_failure"],
            "extraction_confidence": 0.7 if fields else 0.0,
        }

    def _detect_sections(self, fields: dict[str, Any]) -> list[str]:
        keys = " ".join(fields.keys()).lower()
        sections = []
        if any(x in keys for x in ("revenue", "profit", "income", "pat", "ebit")):
            sections.append("income_statement")
        if any(x in keys for x in ("asset", "liabilit", "equity", "cash")):
            sections.append("balance_sheet")
        if any(x in keys for x in ("operating", "investing", "financing", "cashflow", "cash_flow")):
            sections.append("cash_flow")
        return sections or ["unknown"]

    def _fail(self, detail: str, code: str) -> dict[str, Any]:
        return {
            "ok": False,
            "parser_id": self.parser_id,
            "parser_version": self.version,
            "pne_version": VERSION,
            "fields": {},
            "periods": [],
            "sections": [],
            "unknown_fields": [],
            "errors": [code],
            "error_detail": detail,
            "extraction_confidence": 0.0,
        }
