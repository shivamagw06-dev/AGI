"""Company Investor Relations connector."""

from __future__ import annotations

from typing import Any

from app.faa.connectors.base import AcquisitionConnector
from app.faa.connectors.catalog import COMPANY_IR, resolve_symbol
from app.faa.http_client import HttpClient
from app.faa.models import CandidateDocument, DiscoveryTask, FetchedDocument, sha256_text, utc_now

_DOC_KEY = {
    "annual_report": "annual",
    "quarterly_report": "quarterly",
    "quarterly_result": "quarterly",
    "investor_presentation": "presentation",
    "transcript": "transcript",
    "conference_call": "transcript",
    "news": "news",
}


class CompanyIrConnector(AcquisitionConnector):
    connector_id = "company_ir"
    name = "Company Investor Relations"
    tier = 1
    max_per_minute = 20
    document_types = [
        "annual_report",
        "quarterly_report",
        "investor_presentation",
        "transcript",
        "conference_call",
        "news",
    ]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        sym = resolve_symbol(task.company, task.symbol)
        if not sym or sym not in COMPANY_IR:
            if task.preferred_url:
                return [
                    CandidateDocument(
                        title=task.description,
                        url=task.preferred_url,
                        connector_id=self.connector_id,
                        document_type=task.document_type,
                        company=task.company,
                        symbol=task.symbol,
                        organisation=task.company or "",
                        discovery_task_id=task.task_id,
                        metadata={"generic": True},
                    )
                ]
            return []

        profile = COMPANY_IR[sym]
        key = _DOC_KEY.get(task.document_type, "ir_home")
        url = profile.get(key) or profile.get("ir_home")
        if not url:
            return []
        out = [
            CandidateDocument(
                title=f"{profile['company']} — {task.description}",
                url=url,
                connector_id=self.connector_id,
                document_type=task.document_type or "investor_relations",
                company=profile["company"],
                symbol=sym,
                organisation=profile["company"],
                discovery_task_id=task.task_id,
                metadata={"ir_home": profile.get("ir_home"), "doc_key": key, "authority": 10 if "report" in task.document_type else 8},
            )
        ]
        # Also surface IR home for broader crawl target
        if key != "ir_home" and profile.get("ir_home"):
            out.append(
                CandidateDocument(
                    title=f"{profile['company']} — Investor Relations Hub",
                    url=profile["ir_home"],
                    connector_id=self.connector_id,
                    document_type="investor_relations",
                    company=profile["company"],
                    symbol=sym,
                    organisation=profile["company"],
                    discovery_task_id=task.task_id,
                    metadata={"doc_key": "ir_home", "authority": 8},
                )
            )
        return out

    def fetch(self, candidate: CandidateDocument, client: HttpClient) -> FetchedDocument | None:
        """Prefer Playwright for JS-heavy IR hubs when FAA_PLAYWRIGHT is enabled."""
        url = (candidate.url or "").strip()
        if not url or url.lower().endswith(".pdf"):
            return None
        try:
            from app.faa.playwright_browser import fetch_page, playwright_enabled
        except Exception:
            return None
        if not playwright_enabled():
            return None
        page = fetch_page(url)
        if not page or not (page.get("markdown") or "").strip():
            return None
        text = str(page["markdown"])
        meta: dict[str, Any] = dict(candidate.metadata or {})
        meta.update(
            {
                "enriched_by": "playwright",
                "pdf_links": page.get("pdf_links") or [],
                "ir_js_render": True,
            }
        )
        return FetchedDocument(
            candidate_id=candidate.candidate_id,
            title=page.get("title") or candidate.title,
            url=str(page.get("url") or url),
            connector_id=self.connector_id,
            document_type=candidate.document_type,
            company=candidate.company,
            symbol=candidate.symbol,
            organisation=candidate.organisation,
            published_at=candidate.published_at or utc_now().date().isoformat(),
            content_type="text/plain",
            content_text=text[:200_000],
            content_bytes_len=len(text.encode("utf-8")),
            checksum=sha256_text(text),
            live_fetch=True,
            metadata=meta,
        )
