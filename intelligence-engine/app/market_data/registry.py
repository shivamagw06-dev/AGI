"""Provider registry — plug in providers without changing engine code."""

from __future__ import annotations

from app.market_data.provider_base import Capability, MarketDataProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {}

    def register(self, provider: MarketDataProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> MarketDataProvider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> list[MarketDataProvider]:
        return sorted(self._providers.values(), key=lambda p: (p.priority, p.provider_id))

    def providers_for(self, capability: Capability) -> list[MarketDataProvider]:
        return [
            provider
            for provider in self.list_providers()
            if provider.is_configured() and capability in provider.capabilities()
        ]
