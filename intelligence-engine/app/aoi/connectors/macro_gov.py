"""Macro and government connectors — RBI, SEBI, MoF, MOSPI, PIB."""

from __future__ import annotations

from app.aoi.connector import SourceConnector
from app.aoi.connectors._util import fact, make_artifact
from app.aoi.models import DocumentArtifact, ExtractedFact
from app.aoi.registry import CompanyRegistry


class _StreamConnector(SourceConnector):
    category = "government"

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        _ = registry  # source-agnostic; company registry unused for pure macro streams
        streams = list(self.config.get("streams") or [])
        base = str(self.config.get("base_url") or "")
        out: list[DocumentArtifact] = []
        for stream in streams:
            url = f"{base.rstrip('/')}/{stream}"
            title = f"{self.name} — {stream.replace('_', ' ').title()}"
            content = (
                f"Source: {self.name}\n"
                f"Release: {stream}\n"
                f"Macro / regulatory update for institutional knowledge.\n"
                f"Leading indicators and policy implications.\n"
                f"Affected sectors: Banking, Financial Services, Capital Goods.\n"
            )
            out.append(
                make_artifact(
                    connector_id=self.connector_id,
                    title=title,
                    url=url,
                    doc_type=stream,
                    company_id=None,
                    fmt="html",
                    content=content,
                    metadata={"macro": True, "stream": stream},
                )
            )
        return out

    def download(self, artifact: DocumentArtifact) -> DocumentArtifact:
        art = artifact.model_copy(deep=True)
        art.status = "downloaded"
        art.downloaded_at = art.discovered_at
        return art

    def parse(self, artifact: DocumentArtifact) -> DocumentArtifact:
        art = artifact.model_copy(deep=True)
        art.status = "parsed"
        art.parsed_at = art.discovered_at
        return art

    def extract(self, artifact: DocumentArtifact) -> list[ExtractedFact]:
        return [
            fact(
                field=f"macro_{artifact.doc_type}",
                value_text=(artifact.content_text or artifact.title)[:600],
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                confidence=0.8,
                section="macro",
            ),
            fact(
                field="affected_sectors",
                value_text="Banking, Financial Services, Capital Goods",
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                confidence=0.65,
                section="impact",
            ),
        ]


class RbiConnector(_StreamConnector):
    connector_id = "rbi"
    name = "RBI"
    category = "macro"


class SebiConnector(_StreamConnector):
    connector_id = "sebi"
    name = "SEBI"


class MofConnector(_StreamConnector):
    connector_id = "mof"
    name = "Ministry of Finance"


class MospiConnector(_StreamConnector):
    connector_id = "mospi"
    name = "MOSPI"
    category = "macro"


class PibConnector(_StreamConnector):
    connector_id = "pib"
    name = "PIB"
