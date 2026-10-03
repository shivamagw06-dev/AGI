from __future__ import annotations

from reasoning_providers import (
    AnthropicProvider,
    GoogleProvider,
    LocalModelProvider,
    OpenAIProvider,
    get_reasoning_provider,
)


def test_provider_selection_is_configuration_driven(monkeypatch):
    monkeypatch.setenv("ASK_MODEL_PROVIDER", "anthropic")
    assert isinstance(get_reasoning_provider(), AnthropicProvider)
    assert isinstance(get_reasoning_provider("openai"), OpenAIProvider)
    assert isinstance(get_reasoning_provider("google"), GoogleProvider)
    assert isinstance(get_reasoning_provider("future_agi"), LocalModelProvider)


def test_local_provider_requires_only_an_endpoint(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://model.internal:8000")
    monkeypatch.delenv("LOCAL_MODEL_API_KEY", raising=False)
    assert LocalModelProvider().available() is True
