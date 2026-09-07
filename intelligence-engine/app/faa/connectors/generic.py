"""Generic HTML / PDF URL connectors."""

from __future__ import annotations

from app.faa.connectors.base import AcquisitionConnector
from app.faa.models import CandidateDocument, DiscoveryTask


class GenericHtmlConnector(AcquisitionConnector):
    connector_id = "html_page"
    name = "Generic HTML"
    tier = 6
    max_per_minute = 40
    document_types = ["html", "unknown", "general_web"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if not task.preferred_url:
            return []
        if task.preferred_url.lower().endswith(".pdf"):
            return []
        return [
            CandidateDocument(
                title=task.description or task.preferred_url,
                url=task.preferred_url,
                connector_id=self.connector_id,
                document_type=task.document_type or "html",
                company=task.company,
                symbol=task.symbol,
                organisation=task.company or "web",
                discovery_task_id=task.task_id,
                metadata={"authority": 3},
            )
        ]


class GenericPdfConnector(AcquisitionConnector):
    connector_id = "pdf_url"
    name = "Generic PDF"
    tier = 5
    max_per_minute = 20
    document_types = ["pdf", "annual_report", "quarterly_report", "investor_presentation"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if not task.preferred_url:
            return []
        if ".pdf" not in task.preferred_url.lower():
            return []
        return [
            CandidateDocument(
                title=task.description or task.preferred_url,
                url=task.preferred_url,
                connector_id=self.connector_id,
                document_type=task.document_type or "pdf",
                company=task.company,
                symbol=task.symbol,
                organisation=task.company or "pdf",
                discovery_task_id=task.task_id,
                metadata={"authority": 8},
            )
        ]
