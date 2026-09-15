"""Document timeline — publication order without recommendations."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents import store


def company_document_timeline(ticker: str) -> dict[str, Any]:
    docs = store.list_documents(ticker=ticker)
    events = [
        {
            "document_id": d.get("document_id"),
            "type": d.get("type"),
            "title": d.get("title"),
            "published_date": d.get("published_date"),
            "available_from": d.get("available_from"),
            "source": d.get("source"),
        }
        for d in docs
    ]
    events.sort(key=lambda e: str(e.get("available_from") or ""))
    return {
        "company": ticker.upper(),
        "n": len(events),
        "events": events,
        "recommendation": None,
        "fabricated": False,
    }
