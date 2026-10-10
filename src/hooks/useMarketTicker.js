import { useMarketDataContext } from '@/contexts/MarketDataContext';

export default function useMarketTicker() {
  const { intelligence, loading } = useMarketDataContext();
  return {
    items: intelligence.insightStrip || [],
    loading,
    source: 'agi-intelligence',
  };
}
