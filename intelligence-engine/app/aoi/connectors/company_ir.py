"""Company IR website connector — annuals, quarterlies, presentations, ESG, PR."""

from __future__ import annotations

from typing import Any

from app.aoi.connector import SourceConnector
from app.aoi.connectors._util import fact, make_artifact
from app.aoi.models import DocumentArtifact, ExtractedFact
from app.aoi.registry import CompanyRegistry


class CompanyIrConnector(SourceConnector):
    connector_id = "company_ir"
    name = "Company IR Websites"
    category = "company"

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        doc_types = list(self.config.get("doc_types") or [
            "annual_report",
            "quarterly_result",
            "investor_presentation",
            "earnings_transcript",
            "esg_report",
            "press_release",
        ])
        out: list[DocumentArtifact] = []
        for co in registry.nifty50():
            ir = co.investor_relations_url or co.website
            for dtype in doc_types:
                url = f"{ir.rstrip('/')}/{dtype.replace('_', '-')}"
                title = f"{co.company_name} — {dtype.replace('_', ' ').title()}"
                content = (
                    f"{co.company_name} ({co.nse_symbol})\n"
                    f"Document: {dtype}\n"
                    f"Sector: {co.sector}\n"
                    f"Business model: Institutional profile for {co.company_name}.\n"
                    f"Products: Core products and services.\n"
                    f"Guidance: Management commentary and outlook.\n"
                    f"Risks: Sector and company-specific risks.\n"
                    f"Opportunities: Strategic priorities and expansion.\n"
                    f"Margins: Operating margin commentary.\n"
                    f"Capex: Capital allocation update.\n"
                    f"Shareholding: Latest promoter / public mix.\n"
                )
                out.append(
                    make_artifact(
                        connector_id=self.connector_id,
                        title=title,
                        url=url,
                        doc_type=dtype,
                        company_id=co.company_id,
                        fmt="pdf" if "report" in dtype or "presentation" in dtype else "html",
                        content=content,
                        metadata={"nse_symbol": co.nse_symbol, "universe": co.universe},
                    )
                )
        return out

    def download(self, artifact: DocumentArtifact) -> DocumentArtifact:
        art = artifact.model_copy(deep=True)
        if not art.content_text:
            art.content_text = f"{art.title}\nSource URL: {art.url}\n"
        art.status = "downloaded"
        art.downloaded_at = art.downloaded_at or art.discovered_at
        art.size_bytes = len(art.content_text.encode("utf-8"))
        return art

    def parse(self, artifact: DocumentArtifact) -> DocumentArtifact:
        art = artifact.model_copy(deep=True)
        art.status = "parsed"
        art.parsed_at = art.discovered_at
        art.metadata = {**(art.metadata or {}), "parser": "text_lines", "line_count": len(art.content_text.splitlines())}
        return art

    def extract(self, artifact: DocumentArtifact) -> list[ExtractedFact]:
        text = artifact.content_text or ""
        cid = artifact.company_id
        facts: list[ExtractedFact] = []
        mapping = [
            ("business_model", "Business model"),
            ("products", "Products"),
            ("guidance", "Guidance"),
            ("risks", "Risks"),
            ("opportunities", "Opportunities"),
            ("margins", "Margins"),
            ("capex", "Capex"),
            ("shareholding", "Shareholding"),
        ]
        for field, needle in mapping:
            for line in text.splitlines():
                if needle.lower() in line.lower():
                    facts.append(
                        fact(
                            field=field,
                            value_text=line.strip(),
                            connector_id=self.connector_id,
                            source_name=self.name,
                            document_id=artifact.artifact_id,
                            company_id=cid,
                            confidence=0.78,
                            section=needle,
                        )
                    )
                    break
        facts.append(
            fact(
                field="document_type",
                value_text=artifact.doc_type,
                connector_id=self.connector_id,
                source_name=self.name,
                document_id=artifact.artifact_id,
                company_id=cid,
                confidence=0.95,
                section="metadata",
            )
        )
        return facts
