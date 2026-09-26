"""WS02 Market Data Platform tests — WBS DATA-001–005."""

from __future__ import annotations

import asyncio
from datetime import date

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.market_data.cache import MarketDataCache
from app.market_data.circuit_breaker import CircuitBreaker
from app.market_data.client import MarketDataClient
from app.market_data.models import MarketDataQuote, Provenance, utcnow
from app.market_data.provider_base import Capability, MarketDataProvider, ProviderError
from app.market_data.providers.finnhub import FinnhubProvider
from app.market_data.providers.fmp import FmpProvider
from app.market_data.providers.indianapi import IndianApiProvider
from app.market_data.rate_limiter import ProviderRateLimitRegistry, RateLimitExceeded
from app.market_data.registry import ProviderRegistry
from app.market_data.retry import compute_backoff_s, retry_async


class FakeProvider(MarketDataProvider):
    def __init__(
        self,
        provider_id: str,
        *,
        priority: int = 10,
        fail_times: int = 0,
        quote: MarketDataQuote | None = None,
        configured: bool = True,
        retryable_fail: bool = True,
    ) -> None:
        self.provider_id = provider_id
        self.priority = priority
        self._fail_times = fail_times
        self._calls = 0
        self._configured = configured
        self._retryable_fail = retryable_fail
        self._quote = quote or MarketDataQuote(
            symbol="RELIANCE",
            last=100.0,
            provenance=self.make_provenance(vendor_as_of="2026-07-24T10:00:00Z"),
        )

    def capabilities(self) -> set[Capability]:
        return {"quote"}

    def is_configured(self) -> bool:
        return self._configured

    async def get_quote(self, symbol: str) -> MarketDataQuote:
        self._calls += 1
        if self._calls <= self._fail_times:
            raise ProviderError(self.provider_id, "transient", retryable=self._retryable_fail)
        q = self._quote.model_copy(deep=True)
        q.symbol = symbol.upper()
        q.provenance = self.make_provenance(vendor_as_of=q.provenance.vendor_as_of)
        return q


@pytest.mark.asyncio
async def test_provider_contract_normalization_indianapi():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ticker": "RELIANCE",
                "currentPrice": 2801.5,
                "open": 2790,
                "dayHigh": 2810,
                "dayLow": 2780,
                "previousClose": 2795,
                "volume": 1000,
                "pChange": 0.23,
                "lastUpdateTime": "2026-07-24 15:30:00",
                "exchange": "NSE",
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        provider = IndianApiProvider(api_key="test", client=http_client)
        quote = await provider.get_quote("reliance")
    assert quote.object_type == "MarketDataQuote"
    assert quote.schema_version == "market_data.quote.v1"
    assert quote.symbol == "RELIANCE"
    assert quote.last == 2801.5
    assert quote.provenance.source == "indianapi"
    assert quote.provenance.pulled_at is not None
    assert quote.provenance.vendor_as_of == "2026-07-24 15:30:00"


@pytest.mark.asyncio
async def test_provider_contract_finnhub_and_fmp():
    def finnhub_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"c": 10.5, "o": 10, "h": 11, "l": 9.5, "pc": 10.2, "d": 0.3, "dp": 2.9, "t": 1})

    def fmp_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"symbol": "AAPL", "price": 190.0, "open": 189, "dayHigh": 191, "dayLow": 188, "previousClose": 189.5, "volume": 1, "change": 0.5, "changesPercentage": 0.26}],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(finnhub_handler)) as client:
        fh = FinnhubProvider(api_key="k", client=client)
        q1 = await fh.get_quote("AAPL")
    async with httpx.AsyncClient(transport=httpx.MockTransport(fmp_handler)) as client:
        fmp = FmpProvider(api_key="k", client=client)
        q2 = await fmp.get_quote("AAPL")
    assert q1.schema_version == "market_data.quote.v1"
    assert q2.schema_version == "market_data.quote.v1"
    assert q1.last == 10.5
    assert q2.last == 190.0


@pytest.mark.asyncio
async def test_retry_retries_then_succeeds():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderError("x", "temp", retryable=True)
        return "ok"

    sleeps: list[float] = []

    async def fake_sleep(delay: float):
        sleeps.append(delay)

    assert await retry_async(flaky, max_attempts=5, sleep=fake_sleep, jitter=0) == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_backoff_increases():
    d0 = compute_backoff_s(0, base_s=0.05, factor=2, max_s=2, jitter=0)
    d1 = compute_backoff_s(1, base_s=0.05, factor=2, max_s=2, jitter=0)
    assert d1 == pytest.approx(0.1)
    assert d1 > d0


@pytest.mark.asyncio
async def test_cache_hit_and_duplicate_coalesce():
    cache = MarketDataCache()
    started = asyncio.Event()
    release = asyncio.Event()
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        started.set()
        await release.wait()
        return MarketDataQuote(
            symbol="X",
            last=1.0,
            provenance=Provenance(
                source="fake",
                provider_id="fake",
                pulled_at=utcnow(),
                vendor_as_of=date(2026, 7, 24),
            ),
        )

    task1 = asyncio.create_task(cache.get_or_set("k", 60, factory))
    await started.wait()
    task2 = asyncio.create_task(cache.get_or_set("k", 60, factory))
    await asyncio.sleep(0.01)
    release.set()
    v1, hit1 = await task1
    v2, hit2 = await task2
    assert calls["n"] == 1
    assert hit1 is False and hit2 is False
    assert cache.coalesced >= 1
    v3, hit3 = await cache.get_or_set("k", 60, factory)
    assert hit3 is True
    assert v3.symbol == "X"
    assert cache.hit_ratio > 0


@pytest.mark.asyncio
async def test_cache_owner_failure_does_not_leave_unretrieved_future():
    cache = MarketDataCache()
    loop = asyncio.get_running_loop()
    contexts = []
    previous = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: contexts.append(context))

    async def failing_factory():
        raise RuntimeError("provider unavailable")

    try:
        with pytest.raises(RuntimeError, match="provider unavailable"):
            await cache.get_or_set("failed", 60, failing_factory)
        await asyncio.sleep(0)
        assert not [
            context
            for context in contexts
            if "Future exception was never retrieved" in str(context.get("message"))
        ]
    finally:
        loop.set_exception_handler(previous)


def test_rate_limiter_blocks_burst():
    registry = ProviderRateLimitRegistry()
    registry.configure("p", rate_per_second=1, burst=1)
    registry.acquire("p")
    with pytest.raises(RateLimitExceeded):
        registry.acquire("p")


@pytest.mark.asyncio
async def test_failover_to_secondary_provider():
    primary = FakeProvider("primary", priority=1, fail_times=100, retryable_fail=True)
    secondary = FakeProvider(
        "secondary",
        priority=2,
        quote=MarketDataQuote(
            symbol="RELIANCE",
            last=200.0,
            provenance=Provenance(
                source="secondary",
                provider_id="secondary",
                pulled_at=utcnow(),
            ),
        ),
    )
    # Make primary fail fast: non-retryable after circuit — use fail_times with max_attempts=1
    client = MarketDataClient(max_attempts=1)
    client.rate_limits.configure("primary", 100, 100)
    client.rate_limits.configure("secondary", 100, 100)
    client.register_provider(primary)
    client.register_provider(secondary)
    quote = await client.get_quote("RELIANCE")
    assert quote.last == 200.0
    assert quote.provenance.provider_id == "secondary"
    assert quote.provenance.cache_hit is False
    assert client.metrics.failover_count >= 1


@pytest.mark.asyncio
async def test_non_retryable_provider_failure_is_attempted_once_before_failover():
    primary = FakeProvider(
        "permanent_failure",
        priority=1,
        fail_times=100,
        retryable_fail=False,
    )
    secondary = FakeProvider("healthy_fallback", priority=2)
    client = MarketDataClient(max_attempts=3)
    client.rate_limits.configure("permanent_failure", 100, 100)
    client.rate_limits.configure("healthy_fallback", 100, 100)
    client.register_provider(primary)
    client.register_provider(secondary)

    quote = await client.get_quote("ZENTEC")

    assert quote.provenance.provider_id == "healthy_fallback"
    assert primary._calls == 1
    assert secondary._calls == 1


@pytest.mark.asyncio
async def test_cache_path_marks_cache_hit_and_is_fast():
    provider = FakeProvider("only", priority=1)
    client = MarketDataClient(quote_ttl_s=60, max_attempts=1)
    client.rate_limits.configure("only", 100, 100)
    client.register_provider(provider)
    q1 = await client.get_quote("RELIANCE")
    q2 = await client.get_quote("RELIANCE")
    assert provider._calls == 1
    assert q1.provenance.cache_hit is False
    assert q2.provenance.cache_hit is True
    snap = client.metrics.snapshot()
    assert snap["cache_hits"] >= 1
    assert snap["cache_hit_ratio"] > 0
    # Warm cache should be well under 250ms p95 target in-process
    assert (snap["latency_cache_p95_ms"] or 0) < 250


@pytest.mark.asyncio
async def test_pull_stamps_required_fields():
    provider = FakeProvider("stamp", priority=1)
    client = MarketDataClient(max_attempts=1)
    client.rate_limits.configure("stamp", 100, 100)
    client.register_provider(provider)
    quote = await client.get_quote("TCS")
    assert quote.provenance.source == "stamp"
    assert quote.provenance.provider_id == "stamp"
    assert quote.provenance.pulled_at is not None
    assert quote.schema_version.endswith(".v1")


def test_circuit_breaker_opens():
    br = CircuitBreaker("x", failure_threshold=2, recovery_timeout_s=60)
    br.record_failure()
    br.record_failure()
    assert br.state.value == "open"
    with pytest.raises(Exception):
        br.before_call()


@pytest.mark.asyncio
async def test_unconfigured_providers_skipped():
    dead = FakeProvider("dead", priority=1, configured=False)
    live = FakeProvider("live", priority=2)
    client = MarketDataClient(max_attempts=1)
    client.rate_limits.configure("live", 100, 100)
    client.register_provider(dead)
    client.register_provider(live)
    quote = await client.get_quote("INFY")
    assert quote.provenance.provider_id == "live"


@pytest.mark.asyncio
async def test_market_data_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/market-data/health")
        assert response.status_code == 200
        body = response.json()
        assert "providers" in body
        assert "metrics" in body
        assert body["status"] in {"verified", "configured_unverified", "unavailable"}
        assert isinstance(body["live_data_verified"], bool)
        assert all("verified_live" in provider for provider in body["providers"])
        ids = {p["provider_id"] for p in body["providers"]}
        assert {"indianapi", "finnhub", "fmp"} <= ids


@pytest.mark.asyncio
async def test_engine_health_separates_availability_from_outputs():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/e02/health")
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is True
        assert isinstance(body["operational"], bool)
        assert body["operational_status"] in {"operational", "ready_no_outputs", "disabled"}


def test_registry_orders_by_priority():
    reg = ProviderRegistry()
    reg.register(FakeProvider("b", priority=20))
    reg.register(FakeProvider("a", priority=10))
    assert [p.provider_id for p in reg.list_providers()] == ["a", "b"]
