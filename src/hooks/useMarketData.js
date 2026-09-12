import { useCallback, useEffect, useState } from "react";
import {
  getIndices,
  getTrending,
  getNews,
  getCommodities,
} from "../api/indianApi";

export default function useMarketData() {
  const [data, setData] = useState({
    indices: [],
    trending: {},
    news: [],
    commodities: [],
    loading: true,
    error: null,
  });

  const loadData = useCallback(async () => {
    const [indicesResult, trendingResult, newsResult, commoditiesResult] =
      await Promise.allSettled([getIndices(), getTrending(), getNews(), getCommodities()]);

    const failed = [indicesResult, trendingResult, newsResult, commoditiesResult]
      .find((result) => result.status === "rejected");

    if (failed) console.error("Market-data refresh failed:", failed.reason);

    setData((current) => ({
      indices: indicesResult.status === "fulfilled"
        ? indicesResult.value.indices || []
        : current.indices,
      trending: trendingResult.status === "fulfilled"
        ? trendingResult.value.trending_stocks || {}
        : current.trending,
      news: newsResult.status === "fulfilled" ? newsResult.value || [] : current.news,
      commodities: commoditiesResult.status === "fulfilled"
        ? commoditiesResult.value || []
        : current.commodities,
      loading: false,
      error: failed ? "Some live market data is temporarily unavailable." : null,
    }));
  }, []);

  useEffect(() => {
    loadData();

    const interval = setInterval(loadData, 60000);

    return () => clearInterval(interval);
  }, [loadData]);

  return data;
}
