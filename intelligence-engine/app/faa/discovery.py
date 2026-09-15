"""Discovery Engine — multi-task retrieval plans, independent connector execution."""

from __future__ import annotations

from typing import Any

from app.faa.connectors import build_connectors
from app.faa.connectors.base import AcquisitionConnector
from app.faa.models import CandidateDocument, DiscoveryTask
from app.fre.planner import plan_retrieval
from app.fre.understanding import understand_query

_TYPE_TO_CONNECTORS: dict[str, list[str]] = {
    "annual_report": ["company_ir", "pdf_url", "search_api"],
    "quarterly_report": ["company_ir", "pdf_url", "search_api"],
    "investor_presentation": ["company_ir", "pdf_url"],
    "transcript": ["company_ir", "search_api"],
    "conference_call": ["company_ir", "search_api"],
    "exchange_filing": ["nse", "bse"],
    "nse_bse_filing": ["nse", "bse"],
    "news": ["news", "rss", "search_api", "tavily", "exa", "firecrawl", "playwright"],
    "government": ["rbi", "sebi", "government", "pib", "mca", "playwright"],
    "rbi": ["rbi", "rss", "playwright"],
    "sebi": ["sebi", "rss", "playwright"],
    # Research path: Exa → Firecrawl → Playwright JS pages → Tavily
    "industry_report": ["search_api", "exa", "firecrawl", "playwright", "tavily"],
    "research_publication": ["search_api", "exa", "firecrawl", "playwright"],
    "investor_relations": ["company_ir", "playwright", "search_api"],
    "fred": ["search_api", "exa", "playwright"],
    "imf": ["search_api", "exa", "playwright"],
    "world_bank": ["search_api", "exa", "playwright"],
    "rss": ["rss"],
    "html": ["html_page", "playwright"],
    "pdf": ["pdf_url"],
}


class DiscoveryService:
    def __init__(self, *, live_fetch: bool = False, connectors: dict[str, AcquisitionConnector] | None = None) -> None:
        self.connectors = connectors or build_connectors(live_fetch=live_fetch)

    def build_tasks(self, query: str, *, aoi: Any | None = None) -> list[DiscoveryTask]:
        ud = understand_query(query, aoi=aoi)
        plan = plan_retrieval(query, aoi=aoi, understanding=ud)
        tasks: list[DiscoveryTask] = []

        for t in plan.tasks:
            connectors: list[str] = []
            for dt in t.document_types:
                for cid in _TYPE_TO_CONNECTORS.get(dt, ["search_api"]):
                    if cid not in connectors and cid in self.connectors:
                        connectors.append(cid)
            if not connectors:
                connectors = ["search_api"] if "search_api" in self.connectors else list(self.connectors)[:1]
            for cid in connectors:
                tasks.append(
                    DiscoveryTask(
                        description=t.description,
                        connector_id=cid,
                        query=f"{ud.primary_entity or ''} {t.description}".strip(),
                        company=t.company or (ud.companies[0] if ud.companies else None),
                        symbol=t.symbol or (ud.symbols[0] if ud.symbols else ud.primary_entity),
                        document_type=(t.document_types[0] if t.document_types else "unknown"),
                        priority=t.priority,
                    )
                )

        entity = ud.primary_entity
        company = ud.companies[0] if ud.companies else None
        if entity:
            forced = [
                ("company_ir", "Latest annual report", "annual_report", 1),
                ("company_ir", "Latest quarterly report", "quarterly_report", 1),
                ("company_ir", "Investor presentation", "investor_presentation", 2),
                ("company_ir", "Conference call transcript", "transcript", 2),
                ("nse", "Exchange filings NSE", "exchange_filing", 2),
                ("bse", "Exchange filings BSE", "exchange_filing", 2),
                ("news", "Latest news", "news", 3),
                ("rss", "Regulator / news RSS", "rss", 3),
                ("rbi", "Government / RBI policy", "government", 4),
                ("sebi", "SEBI notifications", "government", 4),
                ("search_api", "Industry / peer / macro context", "industry_report", 5),
                ("exa", "Semantic research context", "research_publication", 5),
            ]
            for cid, desc, dtype, pri in forced:
                if cid not in self.connectors:
                    continue
                tasks.append(
                    DiscoveryTask(
                        description=desc,
                        connector_id=cid,
                        query=f"{entity} {desc}",
                        company=company,
                        symbol=entity,
                        document_type=dtype,
                        priority=pri,
                    )
                )

        # Peer discovery for investment analysis
        if ud.intent in {"investment_analysis", "comparison"} and entity:
            peers = {
                "RELIANCE": ["BHARTIARTL", "ONGC"],
                "INFY": ["TCS", "WIPRO"],
                "TCS": ["INFY", "WIPRO"],
                "HDFCBANK": ["ICICIBANK", "SBIN"],
            }.get(entity.upper(), [])
            for peer in peers:
                tasks.append(
                    DiscoveryTask(
                        description=f"Peer update — {peer}",
                        connector_id="news",
                        query=f"{peer} latest results",
                        company=peer,
                        symbol=peer,
                        document_type="news",
                        priority=5,
                    )
                )

        seen = set()
        unique: list[DiscoveryTask] = []
        for task in sorted(tasks, key=lambda x: (x.priority, x.connector_id)):
            key = (task.connector_id, task.description, task.symbol, task.document_type)
            if key in seen:
                continue
            seen.add(key)
            unique.append(task)
        return unique

    def discover(self, query: str, *, aoi: Any | None = None, limit: int = 40) -> tuple[list[DiscoveryTask], list[CandidateDocument]]:
        tasks = self.build_tasks(query, aoi=aoi)
        candidates: list[CandidateDocument] = []
        for task in tasks:
            conn = self.connectors.get(task.connector_id)
            if not conn:
                continue
            try:
                found = conn.search(task)
            except Exception:
                try:
                    found = conn.discover(task)
                except Exception:
                    found = []
            candidates.extend(found)
            if len(candidates) >= limit * 2:
                break

        # Prefer higher-authority / lower-tier connectors when de-duping URLs
        by_url: dict[str, CandidateDocument] = {}
        for c in candidates:
            if not c.url:
                continue
            prev = by_url.get(c.url)
            if prev is None:
                by_url[c.url] = c
                continue
            prev_auth = int((prev.metadata or {}).get("authority") or 0)
            new_auth = int((c.metadata or {}).get("authority") or 0)
            if new_auth > prev_auth:
                by_url[c.url] = c

        # Sort by connector priority then keep limit
        def sort_key(c: CandidateDocument) -> tuple[int, int]:
            conn = self.connectors.get(c.connector_id)
            return (conn.priority() if conn else 99, -int((c.metadata or {}).get("authority") or 0))

        ordered = sorted(by_url.values(), key=sort_key)
        return tasks, ordered[:limit]
