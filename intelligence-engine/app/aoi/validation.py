"""Validation & confidence layer for extracted facts."""

from __future__ import annotations

from app.aoi.models import DocumentArtifact, ExtractedFact


_ALLOWED_PREFIXES = (
    "business_",
    "product",
    "segment",
    "revenue",
    "ebitda",
    "pat",
    "margin",
    "cash",
    "debt",
    "capex",
    "roe",
    "roce",
    "dividend",
    "guidance",
    "risk",
    "opportunit",
    "esg",
    "legal",
    "litigation",
    "corporate",
    "shareholding",
    "expansion",
    "m&a",
    "ma_",
    "geographic",
    "technology",
    "ai_",
    "r&d",
    "patent",
    "government",
    "strategic",
    "management",
    "promoter",
    "board",
    "customer",
    "supplier",
    "competitor",
    "plant",
    "factory",
    "capacity",
    "subsidiary",
    "document_",
    "announcement",
    "macro_",
    "fred_",
    "imf_",
    "worldbank",
    "affected_",
    "board_meeting",
    "financial_filing",
    "monetary_",
    "circular",
    "consultation",
    "regulation",
    "budget",
    "notification",
    "cpi",
    "wpi",
    "gdp",
    "iip",
    "government_announcement",
    "press_release",
    "annual_report",
    "quarterly",
    "investor_",
    "earnings_",
    "esg_",
    "shareholding",
    "corporate_action",
    "development_",
    "weo",
    "country_",
    "macro_series",
)


def validate_facts(facts: list[ExtractedFact], artifact: DocumentArtifact) -> list[ExtractedFact]:
    out: list[ExtractedFact] = []
    for f in facts:
        conf = float(f.confidence or 0)
        if conf < 0.05 or conf > 1.0:
            continue
        if not (f.value_text or f.value is not None):
            continue
        field = (f.field or "").lower()
        if not field:
            continue
        # Soft allow-list: known institutional fields or connector-native macro keys
        if not any(field.startswith(p) or p in field for p in _ALLOWED_PREFIXES):
            # Still accept with reduced confidence for extensibility
            f = f.model_copy(update={"confidence": min(conf, 0.55)})
        if not f.source.connector_id:
            continue
        if f.document_id and artifact.artifact_id and f.document_id != artifact.artifact_id:
            f = f.model_copy(update={"document_id": artifact.artifact_id})
        out.append(f)
    return out
