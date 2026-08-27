import { useMarketDataContext } from '@/contexts/MarketDataContext';

export default function useMarketIntelligence() {
  const { intelligence, loading } = useMarketDataContext();
  return {
    ...intelligence,
    loading,
  };
}
