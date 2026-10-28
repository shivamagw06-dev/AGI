import { API_ORIGIN } from '@/config';

export async function getPortfolioMarketPackage(holdings, days = 400) {
  const response = await fetch(`${API_ORIGIN || ''}/api/market/portfolio-package`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      days,
      instruments: holdings.slice(0, 40).map((holding) => ({
        id: holding.id,
        symbol: holding.symbol,
        asset_name: holding.asset_name,
        asset_type: holding.asset_type,
        market: holding.market,
        currency: holding.currency,
        current_price: holding.current_price,
        price_as_of: holding.price_as_of,
        price_source: holding.price_source,
        provider_key: holding.provider_key,
        isin: holding.isin,
        country: holding.country,
        sector: holding.sector,
      })),
    }),
    signal: AbortSignal.timeout(45_000),
  });
  if (!response.ok) throw new Error(`Portfolio market data unavailable (${response.status})`);
  return response.json();
}
