"""Provider-independent reasoning boundary for AGI.

Models transform bounded evidence; they do not own AGI knowledge or policy.
All adapters return the same response contract so callers remain replaceable.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib import request


@dataclass(frozen=True)
class ReasoningResponse:
    text: str
    provider: str
    model: str
    response_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


class ReasoningProvider(Protocol):
    name: str

    def available(self) -> bool: ...
    def default_model(self) -> str: ...
    def structured_generate(
        self, *, instructions: str, input_text: str, model: str | None = None,
        effort: str = "medium", max_output_tokens: int = 1_400,
        timeout: float = 25.0,
    ) -> ReasoningResponse: ...


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json", **headers}, method="POST")
    with request.urlopen(req, timeout=timeout) as response:  # noqa: S310 - configured provider URL
        return json.loads(response.read().decode("utf-8"))


class OpenAIProvider:
    name = "openai"

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())

    def default_model(self) -> str:
        return os.environ.get("OPENAI_REASONING_MODEL", "gpt-5.6-terra").strip() or "gpt-5.6-terra"

    def structured_generate(self, *, instructions: str, input_text: str, model: str | None = None,
                            effort: str = "medium", max_output_tokens: int = 1_400,
                            timeout: float = 25.0) -> ReasoningResponse:
        from openai import OpenAI

        selected = model or self.default_model()
        response = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"].strip(), timeout=timeout, max_retries=1,
        ).responses.create(
            model=selected, instructions=instructions, input=input_text,
            reasoning={"effort": effort}, max_output_tokens=max_output_tokens, store=False,
        )
        usage = getattr(response, "usage", None)
        return ReasoningResponse(
            text=str(getattr(response, "output_text", "") or ""), provider=self.name,
            model=str(getattr(response, "model", selected) or selected),
            response_id=getattr(response, "id", None),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None), finish_reason="stop",
        )


class AnthropicProvider:
    name = "anthropic"

    def available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    def default_model(self) -> str:
        return os.environ.get("ANTHROPIC_REASONING_MODEL", "claude-sonnet-4-5").strip() or "claude-sonnet-4-5"

    def structured_generate(self, *, instructions: str, input_text: str, model: str | None = None,
                            effort: str = "medium", max_output_tokens: int = 1_400,
                            timeout: float = 25.0) -> ReasoningResponse:
        del effort
        selected = model or self.default_model()
        payload = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"model": selected, "max_tokens": max_output_tokens, "system": instructions,
             "messages": [{"role": "user", "content": f"Return valid JSON only.\n\n{input_text}"}]},
            {"x-api-key": os.environ["ANTHROPIC_API_KEY"].strip(), "anthropic-version": "2023-06-01"}, timeout,
        )
        text = "".join(str(item.get("text") or "") for item in payload.get("content") or [] if item.get("type") == "text")
        usage = payload.get("usage") or {}
        return ReasoningResponse(text=text, provider=self.name, model=payload.get("model") or selected,
                                 response_id=payload.get("id"), input_tokens=usage.get("input_tokens"),
                                 output_tokens=usage.get("output_tokens"), finish_reason=payload.get("stop_reason"))


class GoogleProvider:
    name = "google"

    def _key(self) -> str:
        return next((os.environ.get(key, "").strip() for key in
                     ("GEMINI_API_KEY", "GOOGLE_GEMINI_API_KEY", "GOOGLE_API_KEY")
                     if os.environ.get(key, "").strip()), "")

    def available(self) -> bool:
        return bool(self._key())

    def default_model(self) -> str:
        return os.environ.get("GOOGLE_REASONING_MODEL", "gemini-2.5-pro").strip() or "gemini-2.5-pro"

    def structured_generate(self, *, instructions: str, input_text: str, model: str | None = None,
                            effort: str = "medium", max_output_tokens: int = 1_400,
                            timeout: float = 25.0) -> ReasoningResponse:
        del effort
        selected = model or self.default_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected}:generateContent?key={self._key()}"
        payload = _post_json(url, {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": input_text}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": max_output_tokens},
        }, {}, timeout)
        candidate = (payload.get("candidates") or [{}])[0]
        text = "".join(str(part.get("text") or "") for part in ((candidate.get("content") or {}).get("parts") or []))
        usage = payload.get("usageMetadata") or {}
        return ReasoningResponse(text=text, provider=self.name, model=payload.get("modelVersion") or selected,
                                 input_tokens=usage.get("promptTokenCount"), output_tokens=usage.get("candidatesTokenCount"),
                                 finish_reason=candidate.get("finishReason"))


class LocalModelProvider:
    name = "local"

    def _base_url(self) -> str:
        return os.environ.get("LOCAL_MODEL_BASE_URL", "").strip().rstrip("/")

    def available(self) -> bool:
        return bool(self._base_url())

    def default_model(self) -> str:
        return os.environ.get("LOCAL_REASONING_MODEL", "agi-local").strip() or "agi-local"

    def structured_generate(self, *, instructions: str, input_text: str, model: str | None = None,
                            effort: str = "medium", max_output_tokens: int = 1_400,
                            timeout: float = 25.0) -> ReasoningResponse:
        del effort
        selected = model or self.default_model()
        key = os.environ.get("LOCAL_MODEL_API_KEY", "").strip()
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        payload = _post_json(f"{self._base_url()}/v1/chat/completions", {
            "model": selected, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": instructions},
                         {"role": "user", "content": input_text}],
            "max_tokens": max_output_tokens, "temperature": 0.1,
        }, headers, timeout)
        choice = (payload.get("choices") or [{}])[0]
        usage = payload.get("usage") or {}
        return ReasoningResponse(text=str((choice.get("message") or {}).get("content") or ""),
                                 provider=self.name, model=payload.get("model") or selected,
                                 response_id=payload.get("id"), input_tokens=usage.get("prompt_tokens"),
                                 output_tokens=usage.get("completion_tokens"), finish_reason=choice.get("finish_reason"))


_PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "gemini": GoogleProvider,
    "local": LocalModelProvider,
    "future_agi": LocalModelProvider,
}


def configured_provider_name() -> str:
    return (os.environ.get("ASK_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER")
            or os.environ.get("AGI_REASONING_PROVIDER") or "openai").strip().lower()


def get_reasoning_provider(name: str | None = None) -> ReasoningProvider:
    selected = (name or configured_provider_name()).strip().lower()
    provider_type = _PROVIDERS.get(selected)
    if provider_type is None:
        raise ValueError(f"unsupported_reasoning_provider:{selected}")
    return provider_type()

