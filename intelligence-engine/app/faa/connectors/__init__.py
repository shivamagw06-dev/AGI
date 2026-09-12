"""FAA acquisition connectors registry."""

from __future__ import annotations

from typing import Any

from app.faa.connectors.base import AcquisitionConnector
from app.faa.connectors.company_ir import CompanyIrConnector
from app.faa.connectors.exchanges import (
    BseConnector,
    GovernmentConnector,
    McaConnector,
    NseConnector,
    PibConnector,
    RbiConnector,
    SebiConnector,
)
from app.faa.connectors.generic import GenericHtmlConnector, GenericPdfConnector
from app.faa.connectors.news import NewsConnector, RssConnector
from app.faa.connectors.search_api import (
    BingConnector,
    ExaConnector,
    FirecrawlSearchConnector,
    GoogleCseConnector,
    PlaywrightSearchConnector,
    SearchApiConnector,
    SerpApiConnector,
    TavilyConnector,
)


def build_connectors(*, live_fetch: bool = False) -> dict[str, AcquisitionConnector]:
    args: dict[str, Any] = {"live_fetch": live_fetch}
    connectors: list[AcquisitionConnector] = [
        CompanyIrConnector(**args),
        NseConnector(**args),
        BseConnector(**args),
        SebiConnector(**args),
        RbiConnector(**args),
        McaConnector(**args),
        PibConnector(**args),
        GovernmentConnector(**args),
        NewsConnector(**args),
        RssConnector(**args),
        SearchApiConnector(**args),
        ExaConnector(**args),
        TavilyConnector(**args),
        FirecrawlSearchConnector(**args),
        PlaywrightSearchConnector(**args),
        SerpApiConnector(**args),
        GoogleCseConnector(**args),
        BingConnector(**args),
        GenericHtmlConnector(**args),
        GenericPdfConnector(**args),
    ]
    return {c.connector_id: c for c in connectors}
