"""Yahoo Finance provider adapter — secondary institutional data (canonical models only).

Priority 40 (after IndianAPI 10, Finnhub 20, FMP 30). Never expose Yahoo-native payloads.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.market_data.models import (
    CalendarEvent,
    CorporateAction,
    FundamentalSnapshot,
    MarketDataQuote,
    OHLCVSeries,
    OptionChain,
)
from app.market_data.provider_base import Capability, MarketDataProvider, ProviderError
from app.market_data.providers.yahoo_mapper import (
    fundamentals_metrics_from_yfinance_info,
    map_calendar_from_quote_summary,
    map_calendar_from_yfinance_package,
    map_corporate_actions_from_chart,
    map_financial_history_from_quote_summary,
    map_financial_history_from_yfinance_package,
    map_fundamentals_from_chart_meta,
    map_fundamentals_from_quote_summary,
    map_ohlcv_from_chart,
    map_option_chain,
    map_quote_from_chart,
    map_search_results,
    map_valuation_snapshot_from_quote_summary,
    map_valuation_snapshot_from_yfinance_info,
)
from app.market_data.providers.yahoo_symbols import to_yahoo_symbol
from app.market_data.providers.yahoo_yfinance import fetch_yfinance_financial_package, yfinance_available


# quoteSummary modules (gated by feature flags in provider)
ALL_MODULES = (
    "assetProfile",
    "summaryDetail",
    "defaultKeyStatistics",
    "financialData",
    "incomeStatementHistory",
    "incomeStatementHistoryQuarterly",
    "balanceSheetHistory",
    "balanceSheetHistoryQuarterly",
    "cashflowStatementHistory",
    "cashflowStatementHistoryQuarterly",
    "earnings",
    "earningsHistory",
    "earningsTrend",
    "recommendationTrend",
    "upgradeDowngradeHistory",
    "institutionOwnership",
    "fundOwnership",
    "majorHoldersBreakdown",
    "insiderTransactions",
    "insiderHolders",
    "netSharePurchaseActivity",
    "secFilings",
    "price",
)


class YahooFinanceProvider(MarketDataProvider):
    provider_id = "yahoo"
    priority = 40  # secondary — after official/IndianAPI/Finnhub/FMP

    def __init__(
        self,
        *,
        enabled: bool = True,
        profile: bool = True,
        financials: bool = True,
        earnings: bool = True,
        valuation: bool = True,
        ownership: bool = True,
        options: bool = True,
        financial_history: bool = True,
        valuation_history: bool = True,
        yfinance_fallback: bool = True,
        base_url: str = "https://query1.finance.yahoo.com",
        quote_summary_base: str = "https://query2.finance.yahoo.com",
        client: httpx.AsyncClient | None = None,
        user_agent: str = "Mozilla/5.0 (compatible; AGIB-YFP/1.0)",
    ) -> None:
        self.enabled = enabled
        self.flag_profile = profile
        self.flag_financials = financials
        self.flag_earnings = earnings
        self.flag_valuation = valuation
        self.flag_ownership = ownership
        self.flag_options = options
        self.flag_financial_history = financial_history
        self.flag_valuation_history = valuation_history
        self.flag_yfinance_fallback = yfinance_fallback
        self.base_url = base_url.rstrip("/")
        self.quote_summary_base = quote_summary_base.rstrip("/")
        self._client = client
        self.user_agent = user_agent
        self._last_sync: str | None = None
        self._last_error: str | None = None
        self._companies_updated = 0
        self._failed_syncs = 0
        self._latencies_ms: list[float] = []
        self._crumb: str | None = None
        self._cookie_header: str | None = None
        self._yfinance_hits = 0

    def capabilities(self) -> set[Capability]:
        caps: set[Capability] = {"quote", "ohlcv", "corporate_action", "fundamental", "calendar_event"}
        if self.flag_options:
            caps.add("option_chain")
        return caps

    def is_configured(self) -> bool:
        return bool(self.enabled)

    def health_extras(self) -> dict[str, Any]:
        avg = sum(self._latencies_ms) / len(self._latencies_ms) if self._latencies_ms else 0.0
        return {
            "last_sync": self._last_sync,
            "companies_updated": self._companies_updated,
            "failed_syncs": self._failed_syncs,
            "average_latency_ms": round(avg, 2),
            "flags": {
                "YAHOO_PROVIDER": self.enabled,
                "YAHOO_PROFILE": self.flag_profile,
                "YAHOO_FINANCIALS": self.flag_financials,
                "YAHOO_EARNINGS": self.flag_earnings,
                "YAHOO_VALUATION": self.flag_valuation,
                "YAHOO_OWNERSHIP": self.flag_ownership,
                "YAHOO_OPTIONS": self.flag_options,
                "YAHOO_FINANCIAL_HISTORY": self.flag_financial_history,
                "YAHOO_VALUATION_HISTORY": self.flag_valuation_history,
                "YAHOO_YFINANCE_FALLBACK": self.flag_yfinance_fallback,
            },
            "yfinance_available": yfinance_available(),
            "yfinance_hits": self._yfinance_hits,
            "last_error": self._last_error,
        }

    def _modules(self) -> list[str]:
        mods: list[str] = ["price"]
        if self.flag_profile:
            mods.append("assetProfile")
        if self.flag_valuation:
            mods.extend(["summaryDetail", "defaultKeyStatistics", "recommendationTrend"])
        if self.flag_financials:
            mods.extend(
                [
                    "financialData",
                    "incomeStatementHistory",
                    "incomeStatementHistoryQuarterly",
                    "balanceSheetHistory",
                    "balanceSheetHistoryQuarterly",
                    "cashflowStatementHistory",
                    "cashflowStatementHistoryQuarterly",
                ]
            )
        if self.flag_earnings:
            mods.extend(["earnings", "earningsHistory", "earningsTrend", "upgradeDowngradeHistory"])
        if self.flag_ownership:
            mods.extend(
                [
                    "institutionOwnership",
                    "fundOwnership",
                    "majorHoldersBreakdown",
                    "insiderTransactions",
                    "insiderHolders",
                    "netSharePurchaseActivity",
                    "secFilings",
                ]
            )
        # de-dupe preserve order
        seen: set[str] = set()
        out: list[str] = []
        for m in mods:
            if m not in seen and m in ALL_MODULES:
                seen.add(m)
                out.append(m)
        return out

    async def _ensure_crumb(self, client: httpx.AsyncClient) -> None:
        """Yahoo quoteSummary requires crumb + cookie; chart often works without."""
        if self._crumb and self._cookie_header:
            return
        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/json"}
        # Seed cookies
        try:
            await client.get("https://fc.yahoo.com", headers=headers, follow_redirects=True)
        except httpx.HTTPError:
            try:
                await client.get("https://finance.yahoo.com", headers=headers, follow_redirects=True)
            except httpx.HTTPError:
                return
        try:
            crumb_resp = await client.get(
                f"{self.base_url}/v1/test/getcrumb",
                headers=headers,
            )
            if crumb_resp.status_code < 400:
                crumb = (crumb_resp.text or "").strip().strip('"')
                # Reject HTML / JSON error bodies (e.g. 406 Not Acceptable payload with 200)
                if (
                    crumb
                    and "html" not in crumb.lower()
                    and "not acceptable" not in crumb.lower()
                    and not crumb.startswith("{")
                ):
                    self._crumb = crumb
        except httpx.HTTPError:
            return

    async def _get(self, url: str, params: dict[str, Any] | None = None, *, need_crumb: bool = False) -> Any:
        if not self.is_configured():
            raise ProviderError(self.provider_id, "YAHOO_PROVIDER disabled", retryable=False)
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        query = dict(params or {})
        t0 = datetime.now(timezone.utc)
        try:
            if self._client is not None:
                if need_crumb:
                    await self._ensure_crumb(self._client)
                    if self._crumb:
                        query["crumb"] = self._crumb
                response = await self._client.get(url, params=query, headers=headers)
                # Retry once on 401 with fresh crumb
                if response.status_code == 401 and need_crumb:
                    self._crumb = None
                    await self._ensure_crumb(self._client)
                    if self._crumb:
                        query["crumb"] = self._crumb
                    response = await self._client.get(url, params=query, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
                    if need_crumb:
                        await self._ensure_crumb(client)
                        if self._crumb:
                            query["crumb"] = self._crumb
                    response = await client.get(url, params=query, headers=headers)
                    if response.status_code == 401 and need_crumb:
                        self._crumb = None
                        await self._ensure_crumb(client)
                        if self._crumb:
                            query["crumb"] = self._crumb
                        response = await client.get(url, params=query, headers=headers)
        except httpx.HTTPError as exc:
            self._failed_syncs += 1
            self._last_error = str(exc)[:200]
            raise ProviderError(self.provider_id, f"transport error: {exc}", retryable=True) from exc
        latency = (datetime.now(timezone.utc) - t0).total_seconds() * 1000.0
        self._latencies_ms.append(latency)
        self._latencies_ms = self._latencies_ms[-200:]
        if response.status_code == 429:
            self._failed_syncs += 1
            self._last_error = "rate limited"
            raise ProviderError(self.provider_id, "rate limited by vendor", retryable=True)
        if response.status_code >= 500:
            self._failed_syncs += 1
            self._last_error = f"vendor {response.status_code}"
            raise ProviderError(self.provider_id, f"vendor {response.status_code}", retryable=True)
        if response.status_code >= 400:
            self._failed_syncs += 1
            self._last_error = f"vendor {response.status_code}"
            # Permanent client failures must NEVER retry (401/402/403/404).
            # Yahoo crumb refresh already ran once above for 401.
            raise ProviderError(
                self.provider_id,
                f"vendor {response.status_code}: {response.text[:200]}",
                retryable=False,
            )
        self._last_sync = datetime.now(timezone.utc).isoformat()
        return response.json()

    async def get_quote(self, symbol: str) -> MarketDataQuote:
        ysym = to_yahoo_symbol(symbol)
        url = f"{self.base_url}/v8/finance/chart/{ysym}"
        payload = await self._get(url, {"interval": "1d", "range": "5d"})
        quote = map_quote_from_chart(payload, symbol=ysym, provenance=self.make_provenance())
        self._companies_updated += 1
        return quote

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> OHLCVSeries:
        ysym = to_yahoo_symbol(symbol)
        # Map AGI interval → Yahoo
        y_interval = {"1d": "1d", "d": "1d", "1h": "1h", "1wk": "1wk", "1mo": "1mo"}.get(interval, "1d")
        params: dict[str, Any] = {"interval": y_interval, "events": "div|split"}
        if start and end:
            params["period1"] = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            params["period2"] = int(datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).timestamp())
        else:
            params["range"] = "1y"
        url = f"{self.base_url}/v8/finance/chart/{ysym}"
        payload = await self._get(url, params)
        return map_ohlcv_from_chart(payload, symbol=ysym, interval=interval, provenance=self.make_provenance())

    async def get_corporate_actions(self, symbol: str) -> list[CorporateAction]:
        ysym = to_yahoo_symbol(symbol)
        end = date.today()
        start = end - timedelta(days=365 * 5)
        url = f"{self.base_url}/v8/finance/chart/{ysym}"
        payload = await self._get(
            url,
            {
                "interval": "1d",
                "events": "div|split",
                "period1": int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp()),
                "period2": int(datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).timestamp()),
            },
        )
        return map_corporate_actions_from_chart(payload, symbol=ysym, provenance=self.make_provenance())

    async def _yfinance_package(self, ysym: str) -> dict[str, Any]:
        if not self.flag_yfinance_fallback:
            return {}
        pkg = await fetch_yfinance_financial_package(ysym)
        if pkg:
            self._yfinance_hits += 1
        return pkg

    @staticmethod
    def _history_nonempty(hist: dict[str, Any]) -> bool:
        counts = (hist or {}).get("counts") or {}
        return any(int(counts.get(k) or 0) > 0 for k in counts)

    async def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        ysym = to_yahoo_symbol(symbol)
        modules = self._modules()
        url = f"{self.quote_summary_base}/v10/finance/quoteSummary/{ysym}"
        try:
            payload = await self._get(url, {"modules": ",".join(modules)}, need_crumb=True)
            snap = map_fundamentals_from_quote_summary(
                payload,
                symbol=ysym,
                provenance=self.make_provenance(),
                modules_enabled=set(modules),
            )
            self._companies_updated += 1
            return snap
        except ProviderError as exc:
            # Crumb / auth failures are common; try yfinance info, then chart meta
            authish = (
                "401" in str(exc)
                or "403" in str(exc)
                or "Unauthorized" in str(exc)
                or "crumb" in str(exc).lower()
            )
            if not authish:
                raise
            yf_metrics: dict[str, Any] = {}
            if self.flag_yfinance_fallback and (self.flag_financials or self.flag_valuation):
                pkg = await self._yfinance_package(ysym)
                yf_metrics = fundamentals_metrics_from_yfinance_info(pkg.get("info") or {})
            chart_url = f"{self.base_url}/v8/finance/chart/{ysym}"
            chart_payload = await self._get(chart_url, {"interval": "1d", "range": "5d"})
            snap = map_fundamentals_from_chart_meta(
                chart_payload,
                symbol=ysym,
                provenance=self.make_provenance(),
            )
            # Soft-fill empty valuation/fundamental fields from yfinance.info
            if yf_metrics:
                merged = dict(snap.metrics or {})
                for k, v in yf_metrics.items():
                    if merged.get(k) in (None, "", 0, 0.0):
                        merged[k] = v
                snap = snap.model_copy(update={"metrics": merged})
            self._companies_updated += 1
            return snap

    async def get_financial_intelligence(self, symbol: str) -> dict[str, Any]:
        """
        Canonical financial + valuation history package for YFP enrichment.
        Never returns Yahoo-native quoteSummary / yfinance payloads.
        Prefer quoteSummary; soft-fallback to yfinance.get_income_stmt family on crumb failure.
        """
        if not self.is_configured():
            return {"enabled": False, "reason": "not_configured", "provider_id": "yahoo"}
        ysym = to_yahoo_symbol(symbol)
        mods: list[str] = ["price"]
        if self.flag_financial_history or self.flag_financials:
            mods.extend(
                [
                    "financialData",
                    "incomeStatementHistory",
                    "incomeStatementHistoryQuarterly",
                    "balanceSheetHistory",
                    "balanceSheetHistoryQuarterly",
                    "cashflowStatementHistory",
                    "cashflowStatementHistoryQuarterly",
                ]
            )
        if self.flag_valuation_history or self.flag_valuation:
            mods.extend(["summaryDetail", "defaultKeyStatistics"])
        seen_m: set[str] = set()
        modules: list[str] = []
        for m in mods:
            if m not in seen_m:
                seen_m.add(m)
                modules.append(m)
        url = f"{self.quote_summary_base}/v10/finance/quoteSummary/{ysym}"
        payload: dict[str, Any] | None = None
        qs_error: str | None = None
        try:
            payload = await self._get(url, {"modules": ",".join(modules)}, need_crumb=True)
        except ProviderError as exc:
            qs_error = str(exc)[:200]

        out: dict[str, Any] = {
            "enabled": True,
            "provider_id": "yahoo",
            "priority": self.priority,
            "symbol": (symbol or "").upper(),
            "financial_history": {},
            "valuation_snapshot": {},
            "fetch_path": "quoteSummary" if payload is not None else None,
        }
        if payload is not None:
            if self.flag_financial_history:
                out["financial_history"] = map_financial_history_from_quote_summary(payload, symbol=ysym)
            if self.flag_valuation_history:
                out["valuation_snapshot"] = map_valuation_snapshot_from_quote_summary(payload, symbol=ysym)

        need_history = self.flag_financial_history and not self._history_nonempty(out.get("financial_history") or {})
        need_valuation = self.flag_valuation_history and not (out.get("valuation_snapshot") or {}).get("metrics")
        if (need_history or need_valuation) and self.flag_yfinance_fallback:
            pkg = await self._yfinance_package(ysym)
            if pkg:
                out["fetch_path"] = "yfinance_fundamentals_timeseries"
                if need_history:
                    out["financial_history"] = map_financial_history_from_yfinance_package(pkg, symbol=ysym)
                if need_valuation:
                    out["valuation_snapshot"] = map_valuation_snapshot_from_yfinance_info(
                        pkg.get("info") or {}, symbol=ysym
                    )
                # Soft earnings / calendar side-channel (canonical keys only)
                out["earnings_dates"] = list(pkg.get("earnings_dates") or [])
                out["earnings_annual"] = list(pkg.get("earnings_annual") or [])
                out["calendar"] = {
                    k: v
                    for k, v in (pkg.get("calendar") or {}).items()
                    if k
                    in {
                        "Earnings Date",
                        "Ex-Dividend Date",
                        "Dividend Date",
                        "Earnings High",
                        "Earnings Low",
                        "Earnings Average",
                        "Revenue High",
                        "Revenue Low",
                        "Revenue Average",
                    }
                }
                out["sec_filings_count"] = len(pkg.get("sec_filings") or [])

        if not self._history_nonempty(out.get("financial_history") or {}) and not (
            out.get("valuation_snapshot") or {}
        ).get("metrics"):
            out["enabled"] = False
            out["error"] = qs_error or "no_financial_intelligence"
            out["fetch_path"] = out.get("fetch_path") or "none"
            return out

        self._companies_updated += 1
        return out

    async def get_calendar_events(
        self,
        *,
        symbol: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarEvent]:
        if not symbol:
            return []
        ysym = to_yahoo_symbol(symbol)
        mods = [m for m in ("earnings", "earningsHistory", "upgradeDowngradeHistory", "secFilings") if m in self._modules() or m in ALL_MODULES]
        if not self.flag_earnings:
            mods = [m for m in mods if m == "secFilings"]
        events: list[CalendarEvent] = []
        if mods:
            url = f"{self.quote_summary_base}/v10/finance/quoteSummary/{ysym}"
            try:
                payload = await self._get(url, {"modules": ",".join(mods)}, need_crumb=True)
                events = map_calendar_from_quote_summary(
                    payload, symbol=ysym, provenance=self.make_provenance()
                )
            except ProviderError:
                events = []
        if not events and self.flag_yfinance_fallback:
            pkg = await self._yfinance_package(ysym)
            if pkg:
                events = map_calendar_from_yfinance_package(
                    pkg, symbol=ysym, provenance=self.make_provenance()
                )
        # Optional date filter (kept permissive — unparseable dates retained)
        if start or end:
            return list(events)
        return events

    async def get_option_chain(self, underlying: str) -> OptionChain:
        if not self.flag_options:
            raise ProviderError(self.provider_id, "YAHOO_OPTIONS disabled", retryable=False)
        ysym = to_yahoo_symbol(underlying)
        url = f"{self.base_url}/v7/finance/options/{ysym}"
        payload = await self._get(url)
        return map_option_chain(payload, underlying=ysym, provenance=self.make_provenance())

    async def search(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        """Canonical symbol search — used by Ask AGI / CID resolution (not a MarketData capability)."""
        q = (query or "").strip()
        if not q:
            return []
        # Prefer local alias resolution first
        from app.market_data.providers.yahoo_symbols import QUERY_ALIASES, NSE_YAHOO, to_yahoo_symbol

        local: list[dict[str, Any]] = []
        lower = q.lower()
        if lower in QUERY_ALIASES:
            ys = QUERY_ALIASES[lower]
            local.append(
                {
                    "symbol": ys.replace(".NS", "").replace(".BO", ""),
                    "yahoo_symbol": ys,
                    "name": q.title(),
                    "exchange": "NSI",
                    "asset_type": "EQUITY",
                    "score": 1.0,
                }
            )
        upper = q.upper()
        if upper in NSE_YAHOO:
            ys = NSE_YAHOO[upper]
            local.append(
                {
                    "symbol": upper,
                    "yahoo_symbol": ys,
                    "name": upper,
                    "exchange": "NSI",
                    "asset_type": "EQUITY",
                    "score": 1.0,
                }
            )
        url = f"{self.base_url}/v1/finance/search"
        try:
            payload = await self._get(url, {"q": q, "quotesCount": limit, "newsCount": 0})
            remote = map_search_results(payload)
        except ProviderError:
            remote = []
        # Merge local first
        seen = {r["yahoo_symbol"] for r in local}
        for r in remote:
            if r.get("yahoo_symbol") not in seen:
                local.append(r)
        return local[:limit]
