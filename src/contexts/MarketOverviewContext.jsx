import React, { createContext, useContext } from "react";
import useMarketOverview from "@/hooks/useMarketOverview";

const MarketOverviewContext = createContext(null);

export function MarketOverviewProvider({ children }) {
  const value = useMarketOverview();
  return (
    <MarketOverviewContext.Provider value={value}>
      {children}
    </MarketOverviewContext.Provider>
  );
}

export function useMarketOverviewContext() {
  const ctx = useContext(MarketOverviewContext);
  if (!ctx) {
    throw new Error("useMarketOverviewContext must be used within MarketOverviewProvider");
  }
  return ctx;
}
