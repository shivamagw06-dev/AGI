"""OpenAI editorial provider — concise rewrite only; AGIB remains the analyst."""

from __future__ import annotations

import time
from typing import Any

from editorial.logging_util import log_editorial_event
from editorial.prompts import EDITORIAL_SYSTEM, build_prompt
from editorial.provider import EditorialProvider
from observability.tracing import llm_span


class OpenAIProvider(EditorialProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or "gpt-4.1-mini").strip() or "gpt-4.1-mini"

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "role": "writer_only",
            "available": bool(self.api_key),
            "model": self.model,
            "never_analyses": True,
            "never_generates_advice": True,
            "never_overrides_recommendation": True,
        }

    async def rewrite(
        self,
        *,
        mode: str,
        structured: dict[str, Any],
        question: str | None = None,
        max_words: int = 80,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        import httpx

        prompt = build_prompt(
            mode=mode,
            structured=structured,
            question=question,
            max_words=max_words,
        )
        started = time.perf_counter()
        with llm_span(
            provider=self.name,
            model=self.model,
            prompt=prompt,
            system=EDITORIAL_SYSTEM,
            tags=["editorial", "writer_only"],
            metadata={"mode": mode, "max_words": max_words},
        ) as span:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "instructions": EDITORIAL_SYSTEM,
                        "input": prompt,
                        "temperature": 0.2,
                        "max_output_tokens": 500,
                    },
                )
            if response.is_success:
                span.end(outputs={"status_code": response.status_code})
            else:
                span.end(error=f"openai_http_{response.status_code}: {response.text[:200]}")

        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if not response.is_success:
            detail = response.text[:300]
            log_editorial_event(
                event="openai_editorial_http_error",
                question=question,
                structured=structured,
                prompt=prompt,
                latency_ms=latency_ms,
                error=f"{response.status_code}: {detail}",
                provider=self.name,
                mode=mode,
            )
            raise RuntimeError(f"OpenAI editorial failed ({response.status_code})")

        payload = response.json()
        text = str(payload.get("output_text") or "").strip()
        if not text:
            parts: list[str] = []
            for item in payload.get("output") or []:
                for content in item.get("content") or []:
                    if content.get("type") == "output_text" and content.get("text"):
                        parts.append(str(content["text"]))
            text = "".join(parts).strip()
        usage = payload.get("usage") or {}
        token_usage = {
            "prompt_tokens": usage.get("input_tokens"),
            "candidates_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }
        if not text:
            raise RuntimeError("OpenAI returned empty editorial text")
        log_editorial_event(
            event="openai_editorial_rewrite_ok",
            question=question,
            structured=structured,
            response=text,
            latency_ms=latency_ms,
            token_usage=token_usage,
            provider=self.name,
            mode=mode,
        )
        return {
            "text": text,
            "model": self.model,
            "provider": self.name,
            "usage": token_usage,
            "latency_ms": latency_ms,
            "prompt": prompt,
            "response_id": payload.get("id"),
        }
