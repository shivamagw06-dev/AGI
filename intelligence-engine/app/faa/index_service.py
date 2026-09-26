"""Index Service — immutable versions + automatic push into FRE."""

from __future__ import annotations

import time
from typing import Any

from app.faa.cache import DocumentCache
from app.faa.models import DocumentVersion, FetchedDocument, utc_now
from app.faa.store import FaaStore
from app.fre.models import FreDocument


class IndexService:
    def __init__(
        self,
        cache: DocumentCache,
        *,
        fre: Any | None = None,
        store: FaaStore | None = None,
    ) -> None:
        self.cache = cache
        self.fre = fre
        self.store = store or FaaStore()
        self._embed_samples: list[float] = []

    def bind_fre(self, fre: Any) -> None:
        self.fre = fre

    def index(
        self,
        documents: list[FreDocument],
        fetched: list[FetchedDocument] | None = None,
    ) -> dict[str, Any]:
        if self.fre is None:
            return {"indexed": 0, "error": "fre_unbound"}

        fetched_by_checksum = {f.checksum: f for f in (fetched or []) if f.checksum}
        versions: list[DocumentVersion] = []
        for doc in documents:
            self.store.put_document(doc)
            src = fetched_by_checksum.get(doc.checksum)
            version = DocumentVersion(
                url=doc.url,
                checksum=doc.checksum,
                title=doc.title,
                connector_id=(src.connector_id if src else doc.source),
                document_type=doc.document_type,
                company=doc.company,
                symbol=doc.symbol,
                status="active",
                etag=src.etag if src else None,
                last_modified=src.last_modified if src else None,
                live_fetch=bool(src.live_fetch) if src else False,
                retrieved_at=utc_now(),
                metadata={"faa_fetch_id": src.fetch_id if src else None},
            )
            stored = self.store.put_version(version)
            versions.append(stored)

        t0 = time.perf_counter()
        result = self.fre.pipeline.ingest_documents(documents, publish_kip=False)
        self._embed_samples.append((time.perf_counter() - t0) * 1000)
        self._embed_samples = self._embed_samples[-100:]

        # Link FRE ids where possible by checksum/url
        fre_docs = getattr(self.fre.store, "documents", {}) or {}
        by_checksum = {d.checksum: d.document_id for d in fre_docs.values() if getattr(d, "checksum", None)}
        for ver in versions:
            fre_id = by_checksum.get(ver.checksum)
            if fre_id:
                self.store.mark_fre_link(ver.document_id, fre_id)
            self.cache.put(
                url=ver.url,
                checksum=ver.checksum,
                title=ver.title,
                document_type=ver.document_type,
                connector_id=ver.connector_id,
                live_fetch=ver.live_fetch,
                fre_document_id=ver.fre_document_id or fre_id,
                etag=ver.etag,
                last_modified=ver.last_modified,
                version=ver.version,
                document_id=ver.document_id,
            )

        return {
            "indexed": len(result.get("ingested") or []),
            "chunks": result.get("chunks") or 0,
            "failed": result.get("failed") or 0,
            "versions": [v.to_dict() for v in versions],
            "fre_snapshot": result.get("snapshot") or {},
            "embed_ms": self.avg_embed_ms,
        }

    @property
    def avg_embed_ms(self) -> float:
        if not self._embed_samples:
            return 0.0
        return sum(self._embed_samples) / len(self._embed_samples)
