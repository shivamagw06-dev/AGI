from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import httpx
from app.market_data.providers.yahoo import YahooFinanceProvider

@dataclass(frozen=True)
class PricePoint:
    symbol: str; price: float; previous_close: float | None; currency: str; source: str; as_of: str

class FounderPriceResolver:
    def __init__(self) -> None:
        self.yahoo = YahooFinanceProvider(); self.upstox_token = os.environ.get("UPSTOX_ACCESS_TOKEN") or ""; self._amfi = None
    async def quote(self, holding: dict[str, Any]) -> PricePoint:
        asset_type = str(holding.get("asset_type") or ""); currency = str(holding.get("currency") or "INR").upper(); provider_key = str(holding.get("provider_key") or "").strip()
        if asset_type == "mutual_fund": return await self._amfi_quote(holding, provider_key)
        if currency == "INR" and asset_type in {"indian_stock", "etf"} and provider_key and self.upstox_token: return await self._upstox_quote(holding, provider_key)
        symbol = provider_key or str(holding.get("symbol") or "")
        if currency == "INR" and asset_type in {"indian_stock", "etf"} and not symbol.endswith((".NS", ".BO")): symbol = f"{symbol}.NS"
        quote = await self.yahoo.get_quote(symbol)
        if quote.last is None or float(quote.last) <= 0: raise ValueError(f"Yahoo returned no valid price for {symbol}")
        raw_as_of = quote.provenance.vendor_as_of or quote.provenance.pulled_at
        return PricePoint(str(holding.get("symbol") or symbol), float(quote.last), float(quote.previous_close) if quote.previous_close else None, quote.currency or currency, "yahoo_canonical", raw_as_of.isoformat() if hasattr(raw_as_of, "isoformat") else str(raw_as_of))
    async def fx_usdinr(self) -> PricePoint:
        quote = await self.yahoo.get_quote("USDINR=X")
        if quote.last is None or float(quote.last) <= 0: raise ValueError("USD/INR quote unavailable")
        return PricePoint("USDINR", float(quote.last), quote.previous_close, "INR", "yahoo_fx", datetime.now(timezone.utc).isoformat())
    async def benchmark_return(self, components: str):
        parsed = []
        for part in str(components or "").split(","):
            symbol, _, weight = part.strip().partition(":")
            if symbol and weight: parsed.append((symbol, float(weight)))
        total = sum(weight for _, weight in parsed)
        if not parsed or total <= 0: return None, {}
        blended = 0.0; returns = {}
        for symbol, weight in parsed:
            quote = await self.yahoo.get_quote(symbol)
            if quote.last is None or not quote.previous_close: raise ValueError(f"Benchmark quote incomplete for {symbol}")
            ret = float(quote.last) / float(quote.previous_close) - 1; returns[symbol] = ret * 100; blended += ret * weight / total
        return blended, returns
    async def _upstox_quote(self, holding, instrument_key):
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.upstox_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client: response = await client.get("https://api.upstox.com/v2/market-quote/ltp", params={"instrument_key": instrument_key}, headers=headers)
        response.raise_for_status(); row = next(iter((response.json().get("data") or {}).values()), None); price = float((row or {}).get("last_price") or 0)
        if price <= 0: raise ValueError(f"Upstox returned no valid price for {holding.get('symbol')}")
        return PricePoint(str(holding.get("symbol")), price, None, "INR", "upstox_ltp", datetime.now(timezone.utc).isoformat())
    async def _amfi_quote(self, holding, scheme_code):
        if not scheme_code: raise ValueError(f"AMFI scheme code missing for {holding.get('symbol')}")
        if self._amfi is None:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client: response = await client.get("https://www.amfiindia.com/spages/NAVAll.txt")
            response.raise_for_status(); parsed = {}
            for line in response.text.splitlines():
                parts = line.split(";")
                if len(parts) >= 6 and parts[0].strip().isdigit():
                    try: parsed[parts[0].strip()] = (float(parts[4]), parts[5].strip())
                    except ValueError: continue
            self._amfi = parsed
        item = self._amfi.get(scheme_code)
        if not item: raise ValueError(f"AMFI NAV unavailable for scheme {scheme_code}")
        return PricePoint(str(holding.get("symbol")), item[0], None, "INR", "amfi_nav", item[1])
