"""Read-only document inventory — IDI store or injected offline payloads."""

from __future__ import annotations

import re
from typing import Any


def _reporting_period(doc: dict[str, Any]) -> str | None:
    for key in ("reporting_period", "period", "fiscal_period"):
        if doc.get(key):
            return str(doc[key])
    title = str(doc.get("title") or "")
    m = re.search(r"\bFY\s*'?(\d{2,4})\b", title, re.I)
    if m:
        yy = m.group(1)
        if len(yy) == 2:
            return f"FY20{yy}"
        return f"FY{yy}"
    m = re.search(r"\bQ([1-4])\s*FY\s*'?(\d{2,4})\b", title, re.I)
    if m:
        q, yy = m.group(1), m.group(2)
        if len(yy) == 2:
            yy = f"20{yy}"
        return f"Q{q} FY{yy}"
    pub = str(doc.get("published_date") or "")[:10]
    return pub or None


def documents_from_text(
    *,
    company: str,
    doc_type: str,
    title: str,
    text: str,
    published_date: str,
    document_id: str | None = None,
    source: str = "COMPANY_IR",
    reporting_period: str | None = None,
) -> dict[str, Any]:
    """Parse + chunk offline text without mutating the IDI store.

    Uses a local section parser (IDI-compatible labels) so FIRE-03 does not
    hard-depend on Knowledge Factory package imports for injected fixtures.
    """
    from business_intelligence.parse_local import chunk_parsed_local, parse_document_text

    doc_id = document_id or f"fire03-{company.upper()}-{doc_type.lower()}-{published_date}"
    doc: dict[str, Any] = {
        "document_id": doc_id,
        "company": company.upper(),
        "type": doc_type,
        "title": title,
        "published_date": published_date,
        "available_from": published_date,
        "source": source,
        "language": "en",
        "text": text,
        "reporting_period": reporting_period,
        "mode": "injected",
        "collector": "fire03_inject",
    }
    if not doc.get("reporting_period"):
        doc["reporting_period"] = _reporting_period(doc)
    parsed = parse_document_text(doc)
    chunks = chunk_parsed_local(doc, parsed)
    return {
        "document": doc,
        "chunks": chunks,
        "parsed": parsed,
        "pages": parsed.get("pages") or 1,
        "reporting_period": doc.get("reporting_period"),
    }


def normalize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    doc = dict(bundle.get("document") or {})
    chunks = list(bundle.get("chunks") or [])
    if not chunks and doc.get("text"):
        return documents_from_text(
            company=str(doc.get("company") or "UNKNOWN"),
            doc_type=str(doc.get("type") or "ANNUAL_REPORT"),
            title=str(doc.get("title") or doc.get("type") or "Document"),
            text=str(doc.get("text")),
            published_date=str(doc.get("published_date") or "1970-01-01"),
            document_id=doc.get("document_id"),
            source=str(doc.get("source") or "COMPANY_IR"),
            reporting_period=doc.get("reporting_period"),
        )
    if not doc.get("reporting_period"):
        doc["reporting_period"] = _reporting_period(doc)
    pages = bundle.get("pages")
    if pages is None:
        pages = max((int(c.get("page") or 1) for c in chunks), default=1)
    return {
        "document": doc,
        "chunks": chunks,
        "parsed": bundle.get("parsed"),
        "pages": pages,
        "reporting_period": doc.get("reporting_period"),
    }


def load_document_bundles(
    ticker: str,
    *,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Load official document bundles for a company (read-only)."""
    t = ticker.upper().strip()
    notes: list[str] = []
    bundles: list[dict[str, Any]] = []

    if documents is not None:
        for row in documents:
            bundles.append(normalize_bundle(row))
        notes.append("injected_documents")
    else:
        store = _try_idi_store()
        if store is None:
            notes.append("idi_unavailable")
        else:
            try:
                docs = store.list_documents(ticker=t)
                for d in docs:
                    chunks = store.get_chunks(str(d.get("document_id")))
                    bundles.append(
                        normalize_bundle(
                            {
                                "document": d,
                                "chunks": chunks,
                                "pages": d.get("pages"),
                            }
                        )
                    )
                if not bundles:
                    notes.append("no_idi_documents")
                else:
                    notes.append("idi_store")
            except Exception as exc:  # noqa: BLE001
                notes.append(f"idi_unavailable:{type(exc).__name__}")

    pages_indexed = sum(int(b.get("pages") or 0) for b in bundles)
    return {
        "ticker": t,
        "bundles": bundles,
        "n_documents": len(bundles),
        "pages_indexed": pages_indexed,
        "notes": notes,
        "read_only": True,
        "mutated_idi": False,
        "mutated_warehouse": False,
    }


def _try_idi_store():
    """Lazy IDI store import — soft-fail when KF root deps are unavailable."""
    try:
        import importlib

        return importlib.import_module("knowledge_factory.institutional_documents.store")
    except Exception:  # noqa: BLE001
        return None
