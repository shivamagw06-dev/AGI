"""MarketDataClient — single entry point for engines (canonical objects only)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any, TypeVar

from app.core.logging import get_logger
from app.market_data.cache import MarketDataCache
from app.market_data.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from app.market_data.health import ProviderHealthService
from app.market_data.metrics import MarketDataMetrics, Timer
from app.market_data.models import (
    CalendarEvent,
    CanonicalModel,
    CorporateAction,
    EconomicSeries,
    FundamentalSnapshot,
    MarketDataQuote,
    OHLCVSeries,
    OptionChain,
)
from app.market_data.provider_base import Capability, MarketDataProvider, ProviderError
from app.market_data.providers.finnhub import FinnhubProvider
from app.market_data.providers.fmp import FmpProvider
from app.market_data.providers.indianapi import IndianApiProvider
from app.market_data.providers.yahoo import YahooFinanceProvider
from app.market_data.rate_limiter import ProviderRateLimitRegistry, RateLimitExceeded
from app.market_data.registry import ProviderRegistry
from app.market_data.retry import RetryError, retry_async

log = get_logger(__name__)
T = TypeVar("T", bound=CanonicalModel)
UpdateHandler = Callable[[Any], None]


class _PermanentProviderFailure(Exception):
    def __init__(self, original: ProviderError) -> None:
        self.original = original
        super().__init__(str(original))


class MarketDataClient:
    """Failover-aware market data facade.

    Engines call this client only. Provider-native JSON never leaves adapters.
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        *,
        cache: MarketDataCache | None = None,
        rate_limits: ProviderRateLimitRegistry | None = None,
        circuits: CircuitBreakerRegistry | None = None,
        metrics: MarketDataMetrics | None = None,
        quote_ttl_s: float = 30.0,
        ohlcv_ttl_s: float = 300.0,
        default_ttl_s: float = 120.0,
        max_attempts: int = 3,
    ) -> None:
        self.registry = registry or ProviderRegistry()
        self.cache = cache or MarketDataCache()
        self.rate_limits = rate_limits or ProviderRateLimitRegistry()
        self.circuits = circuits or CircuitBreakerRegistry()
        self.metrics = metrics or MarketDataMetrics()
        self.health = ProviderHealthService(self.registry, self.circuits, self.metrics)
        self.quote_ttl_s = quote_ttl_s
        self.ohlcv_ttl_s = ohlcv_ttl_s
        self.default_ttl_s = default_ttl_s
        self.max_attempts = max_attempts
        self._update_handlers: list[UpdateHandler] = []

    def on_update(self, handler: UpdateHandler) -> None:
        """Subscribe to successful provider pulls (ORCH L2 dirty trigger)."""
        self._update_handlers.append(handler)

    @classmethod
    def from_settings(cls, settings: Any) -> "MarketDataClient":
        client = cls()
        client.registry.register(
            IndianApiProvider(
                api_key=getattr(settings, "indian_api_key", "") or "",
                base_url=getattr(settings, "indian_api_base_url", "https://stock.indianapi.in"),
            )
        )
        client.registry.register(
            FinnhubProvider(
                api_key=getattr(settings, "finnhub_api_key", "") or "",
                base_url=getattr(settings, "finnhub_base_url", "https://finnhub.io/api/v1"),
            )
        )
        client.registry.register(
            FmpProvider(
                api_key=getattr(settings, "fmp_api_key", "") or "",
                base_url=getattr(settings, "fmp_base_url", "https://financialmodelingprep.com/api/v3"),
            )
        )
        # Yahoo — secondary institutional enricher (no API key; feature-flagged)
        client.registry.register(
            YahooFinanceProvider(
                enabled=bool(getattr(settings, "yahoo_provider", True)),
                profile=bool(getattr(settings, "yahoo_profile", True)),
                financials=bool(getattr(settings, "yahoo_financials", True)),
                earnings=bool(getattr(settings, "yahoo_earnings", True)),
                valuation=bool(getattr(settings, "yahoo_valuation", True)),
                ownership=bool(getattr(settings, "yahoo_ownership", True)),
                options=bool(getattr(settings, "yahoo_options", True)),
                financial_history=bool(getattr(settings, "yahoo_financial_history", True)),
                valuation_history=bool(getattr(settings, "yahoo_valuation_history", True)),
                yfinance_fallback=bool(getattr(settings, "yahoo_yfinance_fallback", True)),
                base_url=getattr(settings, "yahoo_base_url", "https://query1.finance.yahoo.com"),
                quote_summary_base=getattr(
                    settings, "yahoo_quote_summary_base", "https://query2.finance.yahoo.com"
                ),
            )
        )
        # Conservative defaults; override in config later if needed.
        client.rate_limits.configure("indianapi", rate_per_second=5, burst=10)
        client.rate_limits.configure("finnhub", rate_per_second=8, burst=15)
        client.rate_limits.configure("fmp", rate_per_second=5, burst=10)
        client.rate_limits.configure("yahoo", rate_per_second=3, burst=6)
        return client

    def register_provider(self, provider: MarketDataProvider) -> None:
        self.registry.register(provider)

    def yahoo_provider(self) -> YahooFinanceProvider | None:
        """Soft access to Yahoo adapter for secondary enrichment / search."""
        provider = self.registry.get("yahoo")
        return provider if isinstance(provider, YahooFinanceProvider) else None

    async def search_symbols(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        """Canonical symbol search via Yahoo provider (secondary). Never returns Yahoo-native payloads."""
        yahoo = self.yahoo_provider()
        if yahoo is None or not yahoo.is_configured():
            return []
        return await yahoo.search(query, limit=limit)

    async def yahoo_enrich(self, symbol: str) -> dict[str, Any]:
        """
        Secondary Yahoo enrichment package for CID / KIP / KF.
        Goes through the Yahoo adapter only; returns canonical dumps (not Yahoo-native JSON).
        Does not replace higher-priority provider results — callers merge softly.

        Request-scoped + TTL cache: resolve once per Ask; reuse across CID/DVC/YFP.
        """
        canon = (symbol or "").upper()
        cache_key = f"yahoo_enrich:{canon}"
        try:
            from app.market_data.providers.yahoo_request_cache import cached_get, cached_set
            from app.market_data.providers.yahoo_symbols import to_yahoo_symbol

            hit = cached_get(cache_key)
            if isinstance(hit, dict):
                return hit
            # Resolve Yahoo symbol once and pin it for this request.
            ysym = to_yahoo_symbol(canon)
            cached_set(f"ysym_resolved:{canon}", ysym)
        except Exception:
            cached_get = cached_set = None  # type: ignore[assignment]
            ysym = canon

        yahoo = self.yahoo_provider()
        if yahoo is None or not yahoo.is_configured():
            return {"enabled": False, "provider_id": "yahoo", "reason": "not_configured"}
        out: dict[str, Any] = {
            "enabled": True,
            "provider_id": "yahoo",
            "priority": yahoo.priority,
            "role": "secondary_enrichment",
            "symbol": canon,
            "yahoo_symbol": ysym if "ysym" in locals() else canon,
        }
        try:
            quote = await yahoo.get_quote(symbol)
            out["quote"] = quote.model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001
            out["quote_error"] = str(exc)[:200]
        try:
            fund = await yahoo.get_fundamentals(symbol)
            out["fundamentals"] = fund.model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001
            out["fundamentals_error"] = str(exc)[:200]
        try:
            actions = await yahoo.get_corporate_actions(symbol)
            out["corporate_actions"] = [a.model_dump(mode="json") for a in actions[:40]]
        except Exception as exc:  # noqa: BLE001
            out["corporate_actions_error"] = str(exc)[:200]
        try:
            events = await yahoo.get_calendar_events(symbol=symbol)
            out["calendar_events"] = [e.model_dump(mode="json") for e in events[:40]]
        except Exception as exc:  # noqa: BLE001
            out["calendar_events_error"] = str(exc)[:200]
        # YFP financial intelligence — canonical history (gated on provider flags)
        try:
            if getattr(yahoo, "flag_financial_history", True) or getattr(yahoo, "flag_valuation_history", True):
                fi = await yahoo.get_financial_intelligence(symbol)
                if fi.get("enabled"):
                    out["financial_history"] = fi.get("financial_history") or {}
                    out["valuation_snapshot"] = fi.get("valuation_snapshot") or {}
                elif fi.get("error"):
                    out["financial_intelligence_error"] = fi.get("error")
        except Exception as exc:  # noqa: BLE001
            out["financial_intelligence_error"] = str(exc)[:200]
        if cached_set is not None:
            try:
                cached_set(cache_key, out)
            except Exception:
                pass
        return out

    async def yahoo_financial_intelligence(self, symbol: str) -> dict[str, Any]:
        """Canonical Yahoo financial/valuation history via provider only (never Yahoo-native)."""
        yahoo = self.yahoo_provider()
        if yahoo is None or not yahoo.is_configured():
            return {"enabled": False, "provider_id": "yahoo", "reason": "not_configured"}
        return await yahoo.get_financial_intelligence(symbol)

    async def validated_package(
        self,
        symbol: str,
        *,
        include_quote: bool = True,
        include_fundamentals: bool = True,
        persist: bool = True,
    ) -> dict[str, Any]:
        """
        DVC V1 — multi-provider validation & consensus package.
        Additive soft path; does not change first-success failover for get_quote/get_fundamentals.
        Returns audited field objects, conflicts, quality scores (never provider-native JSON).
        """
        try:
            from app.core.config import get_settings

            if not bool(getattr(get_settings(), "dvc", True)):
                return {"enabled": False, "reason": "dvc_disabled", "symbol": (symbol or "").upper()}
        except Exception:
            pass
        from dvc.validate import validate_symbol

        return await validate_symbol(
            self,
            symbol,
            include_quote=include_quote,
            include_fundamentals=include_fundamentals,
            persist=persist,
        )

    async def get_quote(self, symbol: str) -> MarketDataQuote:
        return await self._fetch(
            capability="quote",
            cache_key=f"quote:{symbol.upper()}",
            ttl_s=self.quote_ttl_s,
            call=lambda p: p.get_quote(symbol),
        )

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> OHLCVSeries:
        key = f"ohlcv:{symbol.upper()}:{interval}:{start}:{end}"
        return await self._fetch(
            capability="ohlcv",
            cache_key=key,
            ttl_s=self.ohlcv_ttl_s,
            call=lambda p: p.get_ohlcv(symbol, interval=interval, start=start, end=end),
        )

    async def get_corporate_actions(self, symbol: str) -> list[CorporateAction]:
        return await self._fetch_list(
            capability="corporate_action",
            cache_key=f"corp:{symbol.upper()}",
            call=lambda p: p.get_corporate_actions(symbol),
        )

    async def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        return await self._fetch(
            capability="fundamental",
            cache_key=f"fund:{symbol.upper()}",
            ttl_s=self.default_ttl_s,
            call=lambda p: p.get_fundamentals(symbol),
        )

    async def get_option_chain(self, underlying: str) -> OptionChain:
        return await self._fetch(
            capability="option_chain",
            cache_key=f"opt:{underlying.upper()}",
            ttl_s=self.default_ttl_s,
            call=lambda p: p.get_option_chain(underlying),
        )

    async def get_economic_series(self, series_id: str) -> EconomicSeries:
        return await self._fetch(
            capability="economic_series",
            cache_key=f"econ:{series_id}",
            ttl_s=self.default_ttl_s,
            call=lambda p: p.get_economic_series(series_id),
        )

    async def get_calendar_events(
        self,
        *,
        symbol: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarEvent]:
        key = f"cal:{symbol}:{start}:{end}"
        return await self._fetch_list(
            capability="calendar_event",
            cache_key=key,
            call=lambda p: p.get_calendar_events(symbol=symbol, start=start, end=end),
        )

    async def _fetch(
        self,
        *,
        capability: Capability,
        cache_key: str,
        ttl_s: float,
        call: Callable[[MarketDataProvider], Awaitable[T]],
    ) -> T:
        timer = Timer()
        cached = self.cache.get(cache_key)
        if cached is not None:
            latency = timer.ms()
            self.metrics.record_cache_hit(latency)
            # Mark provenance cache_hit without mutating cached object identity issues:
            data = cached.model_copy(deep=True)
            data.provenance = data.provenance.model_copy(update={"cache_hit": True})
            log.info(
                "market_data_cache_hit",
                extra={"extra": {"cache_key": cache_key, "latency_ms": latency}},
            )
            return data

        value, _ = await self.cache.get_or_set(
            cache_key,
            ttl_s,
            lambda: self._fetch_with_failover(capability, call, cache_key=cache_key),
        )
        return value

    async def _fetch_list(
        self,
        *,
        capability: Capability,
        cache_key: str,
        call: Callable[[MarketDataProvider], Awaitable[list[Any]]],
    ) -> list[Any]:
        timer = Timer()
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.metrics.record_cache_hit(timer.ms())
            return cached
        value, _ = await self.cache.get_or_set(
            cache_key,
            self.default_ttl_s,
            lambda: self._fetch_with_failover(capability, call, cache_key=cache_key),
        )
        return value

    async def _fetch_with_failover(
        self,
        capability: Capability,
        call: Callable[[MarketDataProvider], Awaitable[Any]],
        *,
        cache_key: str,
    ) -> Any:
        providers = self.registry.providers_for(capability)
        if not providers:
            raise ProviderError("none", f"no configured provider for {capability}", retryable=False)

        errors: list[str] = []
        for index, provider in enumerate(providers):
            if index > 0:
                self.metrics.record_failover()
            try:
                return await self._call_provider(provider, call, cache_key=cache_key)
            except (ProviderError, RateLimitExceeded, CircuitOpenError, RetryError) as exc:
                msg = str(exc)
                errors.append(msg)
                self.health.record_error(provider.provider_id, msg)
                log.warning(
                    "market_data_provider_failed",
                    extra={
                        "extra": {
                            "provider_id": provider.provider_id,
                            "capability": capability,
                            "error": msg,
                        }
                    },
                )
                continue
        raise ProviderError(
            "failover",
            f"all providers failed for {capability}: {errors}",
            retryable=True,
        )

    async def _call_provider(
        self,
        provider: MarketDataProvider,
        call: Callable[[MarketDataProvider], Awaitable[Any]],
        *,
        cache_key: str,
    ) -> Any:
        breaker = self.circuits.get(provider.provider_id)

        async def _once() -> Any:
            breaker.before_call()
            self.rate_limits.acquire(provider.provider_id)
            timer = Timer()
            try:
                result = await call(provider)
                latency = timer.ms()
                breaker.record_success()
                self.metrics.record_cold_fetch(provider.provider_id, latency, ok=True)
                # Ensure pull stamps exist (DATA-005)
                if isinstance(result, CanonicalModel):
                    if result.provenance.provider_id != provider.provider_id:
                        result.provenance = provider.make_provenance(
                            vendor_as_of=result.provenance.vendor_as_of,
                            request_id=result.provenance.request_id,
                        )
                    result.provenance = result.provenance.model_copy(update={"cache_hit": False})
                elif isinstance(result, list):
                    for item in result:
                        if isinstance(item, CanonicalModel):
                            item.provenance = item.provenance.model_copy(update={"cache_hit": False})
                log.info(
                    "market_data_cold_fetch",
                    extra={
                        "extra": {
                            "provider_id": provider.provider_id,
                            "cache_key": cache_key,
                            "latency_ms": latency,
                        }
                    },
                )
                self._publish_update(cache_key, result)
                return result
            except Exception as exc:
                latency = timer.ms()
                retryable = True
                if isinstance(exc, ProviderError):
                    retryable = exc.retryable
                if retryable:
                    breaker.record_failure()
                else:
                    # Permanent failures used to skip the breaker entirely, so a
                    # revoked key (FMP 403) or an unauthorised endpoint (Yahoo
                    # 401/406) never opened the circuit and was re-attempted for
                    # every symbol in the universe. Park the provider instead.
                    cooldown = getattr(exc, "cooldown_s", None)
                    breaker.record_permanent_failure(cooldown)
                    log.warning(
                        "market_data_provider_parked",
                        extra={
                            "extra": {
                                "provider_id": provider.provider_id,
                                "cache_key": cache_key,
                                "cooldown_s": cooldown or breaker.permanent_recovery_timeout_s,
                                "error": str(exc)[:200],
                            }
                        },
                    )
                self.metrics.record_cold_fetch(provider.provider_id, latency, ok=False)
                raise

        async def _once_retryable() -> Any:
            try:
                return await _once()
            except ProviderError as exc:
                if not exc.retryable:
                    raise _PermanentProviderFailure(exc) from exc
                raise

        try:
            return await retry_async(
                _once_retryable,
                max_attempts=self.max_attempts,
                retry_on=(ProviderError, RateLimitExceeded),
                base_s=0.01,
                max_s=0.2,
                jitter=0.1,
            )
        except RetryError:
            raise
        except _PermanentProviderFailure as exc:
            raise exc.original
        except CircuitOpenError:
            raise

    def _publish_update(self, cache_key: str, result: Any) -> None:
        if not self._update_handlers:
            return
        try:
            from app.orch.l2.models import MarketDataUpdateEvent

            update_type, symbol, as_of, input_keys = _infer_update(cache_key, result)
            event = MarketDataUpdateEvent(
                update_type=update_type,
                symbol=symbol,
                as_of=as_of,
                input_keys=input_keys,
                payload_fingerprint=cache_key,
            )
            for handler in self._update_handlers:
                try:
                    handler(event)
                except Exception as exc:
                    log.warning(
                        "market_data_update_handler_failed",
                        extra={"extra": {"error": str(exc)}},
                    )
        except Exception as exc:
            log.warning("market_data_publish_failed", extra={"extra": {"error": str(exc)}})


def _infer_update(cache_key: str, result: Any) -> tuple[str, str | None, str, list[str]]:
    today = date.today().isoformat()
    if cache_key.startswith("ohlcv:"):
        symbol = getattr(result, "symbol", None) or cache_key.split(":", 1)[1].split(":")[0]
        bars = getattr(result, "bars", None) or []
        as_of = str(getattr(bars[-1], "ts", today))[:10] if bars else today
        return "ohlcv", str(symbol).upper() if symbol else None, as_of, ["ohlcv.close", "ohlcv.high", "ohlcv.low", "ohlcv.volume"]
    if cache_key.startswith("quote:"):
        symbol = getattr(result, "symbol", None) or cache_key.split(":", 1)[1]
        return "quote", str(symbol).upper() if symbol else None, today, ["quote.last"]
    if cache_key.startswith("fundamentals:") or "fundamental" in cache_key:
        symbol = getattr(result, "symbol", None)
        return "fundamentals", str(symbol).upper() if symbol else None, today, ["fundamentals."]
    if "macro" in cache_key or "economic" in cache_key:
        return "macro", None, today, ["macro."]
    return "manual", getattr(result, "symbol", None), today, []
