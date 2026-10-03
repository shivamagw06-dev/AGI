"""LangSmith-oriented HAI traces for Sprint 8.4."""

from __future__ import annotations

from typing import Any

try:
    from app.timeline import traces as _shared

    def begin(name: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        return _shared.begin(name, meta=meta)

    def end(span: dict[str, Any], *, ok: bool = True, output: dict[str, Any] | None = None) -> dict[str, Any]:
        return _shared.end(span, ok=ok, output=output)

    def recent(limit: int = 50) -> list[dict[str, Any]]:
        return _shared.recent(limit)

except Exception:  # pragma: no cover
    from app.hri import traces as _shared

    def begin(name: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        return _shared.begin(name, meta=meta)

    def end(span: dict[str, Any], *, ok: bool = True, output: dict[str, Any] | None = None) -> dict[str, Any]:
        return _shared.end(span, ok=ok, output=output)

    def recent(limit: int = 50) -> list[dict[str, Any]]:
        return _shared.recent(limit)
