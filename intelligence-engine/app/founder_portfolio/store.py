from __future__ import annotations
import os
from typing import Any
import httpx

class FounderPortfolioStore:
    def __init__(self) -> None:
        self.url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").rstrip("/")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SECRET_KEY") or ""
    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)
    async def request(self, method: str, table: str, *, params: dict[str, Any] | None = None, payload: Any = None, prefer: str | None = None) -> list[dict[str, Any]]:
        if not self.configured:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if prefer: headers["Prefer"] = prefer
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, f"{self.url}/rest/v1/{table}", params=params, json=payload, headers=headers)
        response.raise_for_status()
        if not response.content: return []
        body = response.json()
        return body if isinstance(body, list) else [body]
    async def rows(self, table: str, *, select: str = "*", **filters: Any) -> list[dict[str, Any]]:
        return await self.request("GET", table, params={"select": select, **filters})
    async def upsert(self, table: str, payload: dict[str, Any], *, on_conflict: str) -> dict[str, Any]:
        rows = await self.request("POST", table, params={"on_conflict": on_conflict}, payload=payload, prefer="resolution=merge-duplicates,return=representation")
        return rows[0] if rows else payload
    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.request("POST", table, payload=payload, prefer="return=representation")
        return rows[0] if rows else payload
