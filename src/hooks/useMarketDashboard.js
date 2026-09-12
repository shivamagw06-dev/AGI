import { useMarketDataContext } from '@/contexts/MarketDataContext';

export default function useMarketDashboard() {
  const { intelligence, loading } = useMarketDataContext();
  return {
    pulse: intelligence.pulse,
    outlook: intelligence.outlook,
    gainers: intelligence.stocksInFocus?.filter((s) => s.trend === 'Bullish') || [],
    losers: intelligence.stocksInFocus?.filter((s) => s.trend === 'Bearish') || [],
    breadth: intelligence.breadth,
    stocksInFocus: intelligence.stocksInFocus || [],
    sectors: intelligence.sectors || [],
    summary: intelligence.summary,
    loading,
  };
}
