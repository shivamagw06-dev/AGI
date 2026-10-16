import { useCallback, useEffect, useState } from "react";
import {
  getTrending,
  getNews,
  getCommodities,
  getNseMostActive,
  getPriceShockers,
  get52WeekHighLow,
  getIpo,
  getMutualFunds,
  getIndices,
} from "@/api/indianApi";
import { normalizeStock } from "@/lib/marketFormat";

function pickList(payload, ...keys) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  for (const key of keys) {
    if (Array.isArray(payload[key])) return payload[key];
  }
  return [];
}

function flattenMutualFunds(payload, limit = 8) {
  if (!payload || typeof payload !== "object") return [];
  const rows = [];
  for (const category of Object.values(payload)) {
    if (!category || typeof category !== "object") continue;
    for (const subFunds of Object.values(category)) {
      if (!Array.isArray(subFunds)) continue;
      for (const fund of subFunds) {
        rows.push({
          name: fund.fund_name,
          nav: fund.latest_nav,
          change: fund.percentage_change,
          rating: fund.star_rating,
          return1y: fund["1_year_return"],
          category: fund.categoryName || fund.subCategoryName || "",
        });
      }
    }
  }
  return rows
    .filter((f) => f.name && f.return1y != null)
    .sort((a, b) => Number(b.return1y) - Number(a.return1y))
    .slice(0, limit);
}

export default function useMarketOverview() {
  const [data, setData] = useState({
    gainers: [],
    losers: [],
    mostActive: [],
    priceShockers: [],
    weekHighs: [],
    weekLows: [],
    commodities: [],
    news: [],
    ipo: { upcoming: [], open: [], listed: [] },
    mutualFunds: [],
    indices: [],
    loading: true,
    error: null,
  });

  const load = useCallback(async () => {
    const results = await Promise.allSettled([
      getTrending(),
      getNews(1, 8),
      getCommodities(),
      getNseMostActive(),
      getPriceShockers(),
      get52WeekHighLow(),
      getIpo(),
      getMutualFunds(),
      getIndices(),
    ]);

    const [trendingR, newsR, commoditiesR, activeR, shockersR, weekR, ipoR, mfR, indicesR] = results;

    const trending = trendingR.status === "fulfilled" ? trendingR.value : {};
    const gainers = pickList(trending?.trending_stocks, "top_gainers").map(normalizeStock);
    const losers = pickList(trending?.trending_stocks, "top_losers").map(normalizeStock);

    const mostActive = pickList(
      activeR.status === "fulfilled" ? activeR.value : {},
      "NSE_most_active",
      "most_active"
    ).map(normalizeStock);

    const shockersRaw = shockersR.status === "fulfilled" ? shockersR.value : {};
    const priceShockers = [
      ...pickList(shockersRaw, "NSE_PriceShocker", "BSE_PriceShocker"),
    ].map(normalizeStock);

    const weekRaw = weekR.status === "fulfilled" ? weekR.value : {};
    const weekHighs = pickList(weekRaw?.NSE_52WeekHighLow, "high52Week").slice(0, 6);
    const weekLows = pickList(weekRaw?.NSE_52WeekHighLow, "low52Week").slice(0, 6);

    const ipoPayload = ipoR.status === "fulfilled" ? ipoR.value : {};
    const failed = results.find((r) => r.status === "rejected");

    setData({
      gainers: gainers.slice(0, 8),
      losers: losers.slice(0, 8),
      mostActive: mostActive.slice(0, 8),
      priceShockers: priceShockers.slice(0, 8),
      weekHighs,
      weekLows,
      commodities: commoditiesR.status === "fulfilled" ? (commoditiesR.value || []).slice(0, 6) : [],
      news: newsR.status === "fulfilled" ? (Array.isArray(newsR.value) ? newsR.value : []) : [],
      ipo: {
        upcoming: (ipoPayload.upcoming || []).slice(0, 5),
        open: (ipoPayload.open || ipoPayload.current || []).slice(0, 5),
        listed: (ipoPayload.listed || ipoPayload.recently_listed || []).slice(0, 5),
      },
      mutualFunds: flattenMutualFunds(mfR.status === "fulfilled" ? mfR.value : {}),
      indices: indicesR.status === "fulfilled" ? (indicesR.value?.indices || []) : [],
      loading: false,
      error: failed ? "Some market data is temporarily unavailable." : null,
    });
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 120_000);
    return () => clearInterval(id);
  }, [load]);

  return { ...data, refresh: load };
}
