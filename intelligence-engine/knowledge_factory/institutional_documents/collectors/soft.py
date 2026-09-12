"""IDI collectors — official catalog + inject; never fabricate document bodies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.collectors.catalog import catalog_for
from knowledge_factory.institutional_documents.schema import IDI_VERSION, OFFICIAL_SOURCES

SAMPLES = Path(__file__).resolve().parents[1] / "fixtures" / "samples"
COLLECTOR_ID = "idi_soft_collector_v1"


def collect_documents(
    *,
    ticker: str | None = None,
    injected: list[dict[str, Any]] | None = None,
    allow_samples: bool = True,
) -> list[dict[str, Any]]:
    """Collect institutional documents.

    Modes:
      - injected: explicit offline payloads (tests)
      - samples: load catalog-linked sample files (dev/CI; official-structure only)
      - live probe: record IR/exchange URL reachability without fabricating body
    """
    out: list[dict[str, Any]] = []
    if injected is not None:
        for row in injected:
            out.append(_envelope(row, mode="injected"))
        return out

    for entry in catalog_for(ticker):
        if entry.get("source") not in OFFICIAL_SOURCES:
            continue
        body = None
        mode = "live_catalog"
        sample = SAMPLES / str(entry.get("sample_file") or "")
        if allow_samples and sample.exists():
            body = sample.read_text(encoding="utf-8")
            mode = "recorded_sample"
        else:
            # Honest insufficiency: catalog known, body unavailable without sample/inject
            body = None
            mode = "catalog_only"
        out.append(
            _envelope(
                {
                    **entry,
                    "text": body,
                    "pages": _estimate_pages(body) if body else 0,
                },
                mode=mode,
            )
        )
    return out


def _estimate_pages(text: str | None) -> int:
    if not text:
        return 0
    # ~3000 chars/page heuristic for plain-text institutional extracts
    return max(1, (len(text) // 3000) + 1)


def _envelope(row: dict[str, Any], *, mode: str) -> dict[str, Any]:
    company = str(row.get("company") or "").upper()
    doc_type = str(row.get("type") or "EXCHANGE_FILING")
    published = row.get("published_date") or store.utc_now()[:10]
    available = row.get("available_from") or published
    text = row.get("text")
    title = row.get("title") or f"{company} {doc_type}"
    checksum = store.checksum_text(text) if text else None
    raw_rec = None
    if text:
        raw_rec = store.put_raw(
            f"{company}_{doc_type}_{published}.txt",
            text,
            meta={"mode": mode, "source": row.get("source")},
        )
        checksum = raw_rec["checksum"]
    doc_id = row.get("document_id") or f"idi_{company}_{doc_type}_{published}".lower().replace(" ", "_")
    return {
        "ok": bool(text),
        "document_id": doc_id,
        "company": company,
        "type": doc_type,
        "title": title,
        "version": row.get("version") or "1",
        "published_date": published,
        "available_from": available,
        "retrieved_at": store.utc_now(),
        "language": row.get("language") or "en",
        "checksum": checksum,
        "pages": int(row.get("pages") or _estimate_pages(text)),
        "source": row.get("source"),
        "url": row.get("url"),
        "collector": COLLECTOR_ID,
        "collector_version": IDI_VERSION,
        "mode": mode,
        "text": text,
        "fabricated": False,
        "fixture": False,
        "transparent_insufficiency": text is None,
        "provenance": {
            "official_source": row.get("source"),
            "collector": COLLECTOR_ID,
            "retrieved_at": store.utc_now(),
            "url": row.get("url"),
            "checksum": checksum,
            "mode": mode,
            "fabricated": False,
        },
    }
