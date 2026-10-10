"""Evidence mapping — every paragraph section must reference evidence IDs."""

from __future__ import annotations

from typing import Iterable

from institutional_reporting.models import EvidenceItem, InstitutionalReportInput
from institutional_reporting.schema import REPORT_SECTIONS

# Sections that require at least one evidence ID in the rendered paragraph.
PARAGRAPH_SECTIONS = (
    "investment_thesis",
    "business_quality",
    "financial_quality",
    "valuation",
    "risk_assessment",
    "bull_case",
    "bear_case",
    "bottom_line",
)


def evidence_catalog(inp: InstitutionalReportInput) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in inp.evidence:
        rows.append(
            {
                "evidence_id": item.evidence_id,
                "label": item.label,
                "source_type": item.source_type or "",
            }
        )
    return rows


def evidence_ids_for_section(inp: InstitutionalReportInput, section_key: str) -> list[str]:
    """Return evidence IDs mapped to a section; fall back to all IDs for paragraph sections."""
    mapped: list[str] = []
    for item in inp.evidence:
        keys = set(item.section_keys or ())
        if not keys or section_key in keys or "all" in keys:
            if item.evidence_id and item.evidence_id not in mapped:
                mapped.append(item.evidence_id)
    if not mapped and section_key in PARAGRAPH_SECTIONS:
        mapped = [e.evidence_id for e in inp.evidence if e.evidence_id]
    return mapped


def format_supported_by(evidence_ids: Iterable[str], catalog: list[EvidenceItem]) -> str:
    ids = [str(i).strip() for i in evidence_ids if str(i).strip()]
    if not ids:
        return "Supported by\n\n(none)"
    by_id = {e.evidence_id: e for e in catalog}
    lines = ["Supported by", ""]
    for eid in ids:
        item = by_id.get(eid)
        if item:
            label = item.label
            lines.append(eid)
            lines.append(label)
            if item.source_type:
                lines.append(item.source_type)
            lines.append("")
        else:
            lines.append(eid)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_section_evidence_coverage(
    inp: InstitutionalReportInput, section_evidence: dict[str, list[str]]
) -> list[str]:
    errors: list[str] = []
    for key in PARAGRAPH_SECTIONS:
        if key not in REPORT_SECTIONS:
            continue
        ids = section_evidence.get(key) or []
        if not ids:
            errors.append(f"section '{key}' has no evidence mapping")
    return errors
