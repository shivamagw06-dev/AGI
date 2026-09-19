"""Downloader — checksum dedup, metadata tracking, skip unchanged."""

from __future__ import annotations

import datetime as _dt
from typing import Callable

from app.aoi.connector import SourceConnector
from app.aoi.models import DocumentArtifact
from app.aoi.store import AoiStore


class Downloader:
    def __init__(self, store: AoiStore) -> None:
        self.store = store

    def download(
        self,
        connector: SourceConnector,
        artifact: DocumentArtifact,
        *,
        on_retry: Callable[[DocumentArtifact, Exception], None] | None = None,
        max_retries: int = 2,
    ) -> DocumentArtifact:
        if artifact.checksum and artifact.checksum in self.store.known_checksums():
            existing = self.store.artifacts.get(self.store.checksum_index[artifact.checksum])
            if existing:
                skipped = existing.model_copy(deep=True)
                skipped.status = "skipped"
                self.store.metrics.download_success += 1
                return skipped

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                art = connector.download(artifact)
                art.status = "downloaded"
                art.downloaded_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
                art.size_bytes = len((art.content_text or "").encode("utf-8"))
                self.store.upsert_artifact(art)
                self.store.metrics.download_success += 1
                self.store.metrics.knowledge_growth_documents += 1
                return art
            except Exception as exc:  # fault tolerant
                last_exc = exc
                self.store.metrics.retries += 1
                if on_retry:
                    on_retry(artifact, exc)
        failed = artifact.model_copy(deep=True)
        failed.status = "failed"
        failed.error = str(last_exc or "download_failed")
        self.store.upsert_artifact(failed)
        self.store.metrics.download_failed += 1
        self.store.metrics.errors += 1
        return failed
