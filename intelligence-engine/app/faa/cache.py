"""Document cache — URL / ETag / Last-Modified / SHA256 skip logic."""

from __future__ import annotations

from typing import Any

from app.faa.models import sha256_text, utc_now


class DocumentCache:
    def __init__(self) -> None:
        self.by_url: dict[str, dict[str, Any]] = {}
        self.by_checksum: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def lookup(self, url: str) -> dict[str, Any] | None:
        return self.by_url.get((url or "").strip())

    def has_checksum(self, checksum: str) -> bool:
        return bool(checksum) and checksum in self.by_checksum

    def conditional_headers(self, url: str) -> dict[str, str]:
        row = self.lookup(url) or {}
        out: dict[str, str] = {}
        if row.get("etag"):
            out["etag"] = str(row["etag"])
        if row.get("last_modified"):
            out["last_modified"] = str(row["last_modified"])
        return out

    def should_skip(
        self,
        url: str,
        *,
        content_checksum: str | None = None,
        etag: str | None = None,
        not_modified: bool = False,
    ) -> tuple[bool, str | None]:
        if not_modified:
            self.hits += 1
            return True, "http_304_not_modified"
        row = self.lookup(url)
        if content_checksum and self.has_checksum(content_checksum):
            self.hits += 1
            return True, "checksum_exists"
        if row and content_checksum and row.get("checksum") == content_checksum:
            self.hits += 1
            return True, "unchanged_checksum"
        if row and etag and row.get("etag") and row.get("etag") == etag and content_checksum is None:
            self.hits += 1
            return True, "etag_match"
        if row and content_checksum is None and not etag:
            # URL previously acquired — skip unless caller is validating a new body
            self.hits += 1
            return True, "url_cached"
        self.misses += 1
        return False, None

    def put(
        self,
        *,
        url: str,
        checksum: str,
        title: str = "",
        document_type: str = "",
        connector_id: str = "",
        live_fetch: bool = False,
        fre_document_id: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
        version: int = 1,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        prev = self.by_url.get(url)
        row = {
            "url": url,
            "checksum": checksum,
            "title": title,
            "document_type": document_type,
            "connector_id": connector_id,
            "live_fetch": live_fetch,
            "fre_document_id": fre_document_id,
            "etag": etag,
            "last_modified": last_modified,
            "version": version,
            "document_id": document_id,
            "stored_at": utc_now().isoformat(),
            "content_fingerprint": sha256_text(f"{url}|{checksum}"),
        }
        if prev and prev.get("checksum") != checksum:
            row["previous_checksum"] = prev.get("checksum")
            row["versioned"] = True
            row["version"] = int(prev.get("version") or 1) + 1
        self.by_url[url] = row
        if checksum:
            self.by_checksum[checksum] = url
        return row

    def snapshot(self) -> dict[str, Any]:
        total = self.hits + self.misses
        return {
            "urls": len(self.by_url),
            "checksums": len(self.by_checksum),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": round(self.hits / total, 4) if total else 0.0,
        }
