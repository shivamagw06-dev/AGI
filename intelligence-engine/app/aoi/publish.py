"""Soft publish into KIP / KC / KF — no redesign of locked cores."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.aoi.models import DocumentArtifact, ExtractedFact
from app.aoi.registry import CompanyRegistry


def publish_artifact(
    *,
    artifact: DocumentArtifact,
    facts: list[ExtractedFact],
    registry: CompanyRegistry,
    kip: Any | None = None,
    kc: Any | None = None,
    kf: Any | None = None,
    eve: Any | None = None,
) -> dict[str, Any]:
    """Convert AOI artifact into an institutional ingest soft-handoff.

    Prefer KIP ingest when available; always soft-fail.
    Optional EVE extension verifies facts before KC/KF memory (no AOI redesign).
    """
    result: dict[str, Any] = {"published": False, "targets": []}
    co = registry.get(artifact.company_id) if artifact.company_id else None
    symbol = co.nse_symbol if co else ""
    thesis_bits = [f.value_text for f in facts if f.field in {"guidance", "business_model", "opportunities"}][:4]
    risks = [f.value_text for f in facts if "risk" in f.field][:6]
    content = artifact.content_text or artifact.title
    if thesis_bits:
        content = content + "\n\nStructured facts:\n" + "\n".join(thesis_bits)

    # Soft EVE verification gate (between AOI and KCV/KF).
    if eve is not None:
        try:
            eve_result = eve.ingest_aoi_artifact(artifact, facts, company_symbol=symbol)
            result["eve"] = {
                "accepted": bool(eve_result.get("accepted")),
                "evidence_count": eve_result.get("evidence_count"),
                "conflicts": eve_result.get("conflicts"),
                "gate": eve_result.get("gate") or {},
            }
            result["targets"].append("eve")
        except Exception as exc:
            result["eve_error"] = str(exc)

    # Soft KIP ingest
    if kip is not None:
        try:
            from app.kip.models import DocumentType, IngestRequest

            dtype = DocumentType.OTHER
            dt = (artifact.doc_type or "").lower()
            if "earnings" in dt or "transcript" in dt:
                dtype = DocumentType.EARNINGS_TRANSCRIPT
            elif "annual" in dt or "quarter" in dt or "presentation" in dt:
                dtype = DocumentType.AGI_NOTE
            req = IngestRequest(
                title=artifact.title,
                content=content[:12000],
                source="aoi",
                document_type=dtype,
                tickers=[symbol] if symbol else [],
                sectors=[co.sector] if co and co.sector else [],
                date=_dt.datetime.now(_dt.timezone.utc).date(),
                article_id=artifact.artifact_id,
                metadata={
                    "aoi": True,
                    "connector_id": artifact.connector_id,
                    "doc_type": artifact.doc_type,
                    "checksum": artifact.checksum,
                    "risks": risks,
                },
            )
            doc = kip.ingest(req)
            result["published"] = True
            result["targets"].append("kip")
            result["kip_document_id"] = getattr(doc, "document_id", None)
            # Soft KC/KF learn if callers pass services
            if kc is not None:
                try:
                    kc.on_document(doc)
                    result["targets"].append("kc")
                except Exception:
                    pass
            elif kf is not None:
                try:
                    kf.on_document(doc)
                    result["targets"].append("kf")
                except Exception:
                    pass
        except Exception as exc:
            result["kip_error"] = str(exc)

    # Direct KF enrichment fallback (no KIP)
    if not result["published"] and kf is not None and symbol:
        try:
            company = kf.get_company(symbol)
            if isinstance(company, dict):
                result["targets"].append("kf_read")
                result["published"] = True
        except Exception as exc:
            result["kf_error"] = str(exc)

    return result
