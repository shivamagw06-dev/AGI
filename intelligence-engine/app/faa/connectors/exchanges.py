"""NSE / BSE / SEBI / RBI / MCA / Government connectors."""

from __future__ import annotations

from app.faa.connectors.base import AcquisitionConnector
from app.faa.connectors.catalog import EXCHANGE_URLS, resolve_symbol
from app.faa.models import CandidateDocument, DiscoveryTask


class NseConnector(AcquisitionConnector):
    connector_id = "nse"
    name = "NSE Corporate Filings"
    tier = 2
    max_per_minute = 12
    document_types = ["exchange_filing", "nse_bse_filing"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        sym = resolve_symbol(task.company, task.symbol)
        return [
            CandidateDocument(
                title=f"NSE filings — {sym or task.company or 'market'}",
                url=EXCHANGE_URLS["nse_filings"],
                connector_id=self.connector_id,
                document_type="exchange_filing",
                company=task.company,
                symbol=sym,
                organisation="NSE",
                discovery_task_id=task.task_id,
                metadata={"symbol": sym, "authority": 10},
            )
        ]


class BseConnector(AcquisitionConnector):
    connector_id = "bse"
    name = "BSE Announcements"
    tier = 2
    max_per_minute = 12
    document_types = ["exchange_filing", "nse_bse_filing"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        sym = resolve_symbol(task.company, task.symbol)
        return [
            CandidateDocument(
                title=f"BSE announcements — {sym or task.company or 'market'}",
                url=EXCHANGE_URLS["bse_announcements"],
                connector_id=self.connector_id,
                document_type="exchange_filing",
                company=task.company,
                symbol=sym,
                organisation="BSE",
                discovery_task_id=task.task_id,
                metadata={"authority": 10},
            )
        ]


class SebiConnector(AcquisitionConnector):
    connector_id = "sebi"
    name = "SEBI"
    tier = 2
    max_per_minute = 10
    document_types = ["government", "regulation"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        return [
            CandidateDocument(
                title="SEBI circulars / listings",
                url=EXCHANGE_URLS["sebi"],
                connector_id=self.connector_id,
                document_type="government",
                company=task.company,
                symbol=resolve_symbol(task.company, task.symbol),
                organisation="SEBI",
                discovery_task_id=task.task_id,
                metadata={"authority": 9},
            )
        ]


class RbiConnector(AcquisitionConnector):
    connector_id = "rbi"
    name = "RBI Press / Policy"
    tier = 2
    max_per_minute = 10
    document_types = ["government", "rbi", "macro"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        return [
            CandidateDocument(
                title="RBI press releases",
                url=EXCHANGE_URLS["rbi_press"],
                connector_id=self.connector_id,
                document_type="government",
                organisation="RBI",
                discovery_task_id=task.task_id,
                metadata={"authority": 9},
            ),
            CandidateDocument(
                title="RBI bulletins / policy materials",
                url=EXCHANGE_URLS["rbi_mp"],
                connector_id=self.connector_id,
                document_type="government",
                organisation="RBI",
                discovery_task_id=task.task_id,
                metadata={"authority": 9},
            ),
        ]


class McaConnector(AcquisitionConnector):
    connector_id = "mca"
    name = "Ministry of Corporate Affairs"
    tier = 2
    max_per_minute = 8
    document_types = ["government", "corporate_filing"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        return [
            CandidateDocument(
                title="MCA — company filings portal",
                url="https://www.mca.gov.in/content/mca/global/en/home.html",
                connector_id=self.connector_id,
                document_type="government",
                company=task.company,
                symbol=resolve_symbol(task.company, task.symbol),
                organisation="MCA",
                discovery_task_id=task.task_id,
                metadata={"authority": 9},
            )
        ]


class GovernmentConnector(AcquisitionConnector):
    connector_id = "government"
    name = "Government / PIB"
    tier = 2
    max_per_minute = 10
    document_types = ["government", "policy"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        return [
            CandidateDocument(
                title="PIB press releases",
                url="https://pib.gov.in/AllRel.aspx",
                connector_id=self.connector_id,
                document_type="government",
                organisation="PIB",
                discovery_task_id=task.task_id,
                metadata={"authority": 9},
            )
        ]


class PibConnector(AcquisitionConnector):
    connector_id = "pib"
    name = "Press Information Bureau"
    tier = 2
    max_per_minute = 10
    document_types = ["government", "policy"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        return [
            CandidateDocument(
                title="PIB latest releases",
                url="https://www.pib.gov.in/allRel.aspx",
                connector_id=self.connector_id,
                document_type="government",
                organisation="PIB",
                discovery_task_id=task.task_id,
                metadata={"authority": 9},
            )
        ]
