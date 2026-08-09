"""Privacy-minimal durable checkpoints for Ask AGI conversation state."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib import error, parse, request


class CheckpointBackend(Protocol):
    def load(self, thread_id: str) -> dict[str, Any] | None: ...
    def save(self, thread_id: str, payload: dict[str, Any]) -> None: ...
    def delete(self, thread_id: str) -> None: ...


class NullCheckpointBackend:
    def load(self, thread_id: str) -> dict[str, Any] | None:
        return None

    def save(self, thread_id: str, payload: dict[str, Any]) -> None:
        return None

    def delete(self, thread_id: str) -> None:
        return None


class SupabaseConversationCheckpointBackend:
    """Service-role REST adapter; stores compact state, never evidence payloads."""

    table = "conversation_threads"

    def __init__(self, url: str, key: str, *, timeout_seconds: float = 0.5):
        self.url = url.rstrip("/")
        self.key = key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> CheckpointBackend:
        url = (os.environ.get("SUPABASE_URL") or "").strip()
        key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        if not url or not key:
            return NullCheckpointBackend()
        return cls(url, key)

    def _call(self, method: str, suffix: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = request.Request(
            f"{self.url}/rest/v1/{self.table}{suffix}",
            data=data,
            method=method,
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except (error.URLError, error.HTTPError, TimeoutError, ValueError):
            # Conversation persistence is fail-open; research availability must not depend on it.
            return None

    def load(self, thread_id: str) -> dict[str, Any] | None:
        safe = parse.quote(thread_id, safe="")
        rows = self._call("GET", f"?thread_id=eq.{safe}&select=state&limit=1")
        if isinstance(rows, list) and rows and isinstance(rows[0].get("state"), dict):
            return rows[0]["state"]
        return None

    def save(self, thread_id: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        self._call("POST", "?on_conflict=thread_id", {
            "thread_id": thread_id,
            "state": payload,
            "updated_at": now.isoformat(),
            "expires_at": (now + timedelta(days=30)).isoformat(),
        })

    def delete(self, thread_id: str) -> None:
        safe = parse.quote(thread_id, safe="")
        self._call("DELETE", f"?thread_id=eq.{safe}")
