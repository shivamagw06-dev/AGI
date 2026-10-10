"""Global macro connectors — FRED, IMF, World Bank."""

from __future__ import annotations

from app.aoi.connector import SourceConnector
from app.aoi.connectors._util import fact, json_blob, make_artifact
from app.aoi.models import DocumentArtifact, ExtractedFact
from app.aoi.registry import CompanyRegistry


class FredConnector(SourceConnector):
    connector_id = "fred"
    name = "FRED"
    category = "macro"

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        _ = registry
        series = list(self.config.get("series") or ["DFF", "DGS10"])
        base = str(self.config.get("base_url") or "https://api.stlouisfed.org/fred")
        out: list[DocumentArtifact] = []
        for sid in series:
            payload = {"series_id": sid, "source": "FRED", "value": "latest", "unit": "percent_or_index"}
            content = json_blob(payload)
            out.append(
                make_artifact(
                    connector_id=self.connector_id,
                    title=f"FRED series {sid}",
                    url=f"{base.rstrip('/')}/series/observations?series_id={sid}",
                    doc_type="macro_series",
                    fmt="json",
                    content=content,
                    metadata={"series_id": sid},
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
        sid = str((artifact.metadata or {}).get("series_id") or "unknown")
        return [
            fact(
                field=f"fred_{sid.lower()}",
                value_text=artifact.content_text[:400],
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                confidence=0.85,
                section="fred",
                value={"series_id": sid},
            )
        ]


class ImfConnector(SourceConnector):
    connector_id = "imf"
    name = "IMF"
    category = "macro"

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        _ = registry
        streams = list(self.config.get("streams") or ["weo"])
        base = str(self.config.get("base_url") or "")
        return [
            make_artifact(
                connector_id=self.connector_id,
                title=f"IMF {s.replace('_', ' ').title()}",
                url=f"{base.rstrip('/')}/{s}",
                doc_type=s,
                fmt="html",
                content=f"IMF release: {s}. Country forecasts and WEO assumptions for India / global.",
                metadata={"stream": s},
            )
            for s in streams
        ]

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
                field=f"imf_{artifact.doc_type}",
                value_text=(artifact.content_text or artifact.title)[:500],
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                confidence=0.8,
                section="imf",
            )
        ]


class WorldBankConnector(SourceConnector):
    connector_id = "worldbank"
    name = "World Bank"
    category = "macro"

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        _ = registry
        streams = list(self.config.get("streams") or ["development_indicators"])
        base = str(self.config.get("base_url") or "")
        return [
            make_artifact(
                connector_id=self.connector_id,
                title=f"World Bank {s.replace('_', ' ').title()}",
                url=f"{base.rstrip('/')}/{s}",
                doc_type=s,
                fmt="json",
                content=json_blob({"source": "worldbank", "stream": s, "country": "IND"}),
                metadata={"stream": s},
            )
            for s in streams
        ]

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
                field="worldbank_indicator",
                value_text=(artifact.content_text or artifact.title)[:500],
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                confidence=0.8,
                section="worldbank",
            )
        ]
