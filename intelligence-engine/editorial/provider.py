"""Editorial provider interface — swap Gemini / OpenAI / Claude / Mistral / DeepSeek."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EditorialProvider(ABC):
    """Providers rewrite structured AGIB intelligence into prose. Never analyse."""

    name: str = "base"

    @abstractmethod
    async def rewrite(
        self,
        *,
        mode: str,
        structured: dict[str, Any],
        question: str | None = None,
        max_words: int = 60,
    ) -> dict[str, Any]:
        """Return {text, model, usage, latency_ms, provider} or raise on hard failure."""

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "role": "writer_only", "available": False}
