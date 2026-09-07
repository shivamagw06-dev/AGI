"""NSE / BSE disclosure connectors."""

from __future__ import annotations

from app.aoi.connector import SourceConnector
from app.aoi.connectors._util import fact, make_artifact
from app.aoi.models import DocumentArtifact, ExtractedFact
from app.aoi.registry import CompanyRegistry


class _ExchangeConnector(SourceConnector):
    category = "exchange"

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        streams = list(self.config.get("streams") or ["announcements"])
        base = str(self.config.get("base_url") or "")
        out: list[DocumentArtifact] = []
        for co in registry.nifty50():
            for stream in streams:
                url = f"{base.rstrip('/')}/{co.nse_symbol.lower()}/{stream}"
                title = f"{self.name} {stream.replace('_', ' ').title()} — {co.nse_symbol}"
                content = (
                    f"Exchange: {self.connector_id.upper()}\n"
                    f"Company: {co.company_name} ({co.nse_symbol})\n"
                    f"Stream: {stream}\n"
                    f"Announcement summary for {stream.replace('_', ' ')}.\n"
                    f"Corporate action / filing metadata.\n"
                    f"Board meetings and shareholding disclosures when applicable.\n"
                )
                out.append(
                    make_artifact(
                        connector_id=self.connector_id,
                        title=title,
                        url=url,
                        doc_type=stream,
                        company_id=co.company_id,
                        fmt="html",
                        content=content,
                        metadata={"exchange": self.connector_id, "nse_symbol": co.nse_symbol},
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
                field=artifact.doc_type or "announcement",
                value_text=(artifact.content_text or artifact.title)[:500],
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                company_id=artifact.company_id,
                confidence=0.72,
                section=artifact.doc_type,
            )
        ]


class NseConnector(_ExchangeConnector):
    connector_id = "nse"
    name = "NSE"


class BseConnector(_ExchangeConnector):
    connector_id = "bse"
    name = "BSE"
