"""Trusted financial news + RSS connectors."""

from __future__ import annotations

from urllib.parse import quote_plus

from app.faa.connectors.base import AcquisitionConnector
from app.faa.connectors.catalog import resolve_symbol
from app.faa.models import CandidateDocument, DiscoveryTask

_NEWS_HOMES = [
    ("business_standard", "https://www.business-standard.com/search?q={q}", "Business Standard", 7),
    ("moneycontrol", "https://www.moneycontrol.com/news/tags/{q}.html", "Moneycontrol", 7),
    ("economic_times", "https://economictimes.indiatimes.com/topic/{q}", "Economic Times", 7),
    ("reuters", "https://www.reuters.com/site-search/?query={q}", "Reuters", 8),
]

_RSS_FEEDS = [
    ("sebi_rss", "https://www.sebi.gov.in/sebirss.xml", "SEBI RSS"),
    ("rbi_rss", "https://www.rbi.org.in/Scripts/rss.aspx", "RBI RSS"),
    ("moneycontrol_rss", "https://www.moneycontrol.com/rss/latestnews.xml", "Moneycontrol RSS"),
]


class NewsConnector(AcquisitionConnector):
    connector_id = "news"
    name = "Trusted Financial News"
    tier = 4
    max_per_minute = 20
    document_types = ["news"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        sym = resolve_symbol(task.company, task.symbol)
        q = quote_plus(sym or task.company or task.query or "markets")
        out: list[CandidateDocument] = []
        for source, template, org, authority in _NEWS_HOMES:
            out.append(
                CandidateDocument(
                    title=f"{org} — {task.description}",
                    url=template.format(q=q),
                    connector_id=self.connector_id,
                    document_type="news",
                    company=task.company,
                    symbol=sym,
                    organisation=org,
                    discovery_task_id=task.task_id,
                    metadata={"news_source": source, "authority": authority},
                )
            )
        return out[:3]


class RssConnector(AcquisitionConnector):
    connector_id = "rss"
    name = "News / Regulator RSS"
    tier = 4
    max_per_minute = 20
    document_types = ["news", "government", "rss"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        out = []
        for source, url, org in _RSS_FEEDS:
            out.append(
                CandidateDocument(
                    title=f"{org} — {task.description}",
                    url=url,
                    connector_id=self.connector_id,
                    document_type="rss",
                    company=task.company,
                    symbol=resolve_symbol(task.company, task.symbol),
                    organisation=org,
                    discovery_task_id=task.task_id,
                    metadata={"feed": source, "authority": 8 if "SEBI" in org or "RBI" in org else 7},
                )
            )
        return out
