// Market-data requests go through the Express proxy (local dev or Render in production).
import { API_ORIGIN } from "../config";

function resolveOrigin() {
  if (API_ORIGIN) return String(API_ORIGIN).replace(/\/+$/, "");
  // Fallback: Vite inlines import.meta.env.VITE_API_URL at build time.
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv) return String(fromEnv).replace(/\/+$/, "");
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return "http://localhost:5000";
  }
  return "";
}

function apiBase() {
  const origin = resolveOrigin();
  return origin ? `${origin}/api` : "/api";
}

async function request(endpoint) {
  const response = await fetch(`${apiBase()}${endpoint}`, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Market data request failed (${response.status})${detail ? `: ${detail.slice(0, 120)}` : ""}`
    );
  }

  return response.json();
}

function qs(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

// —— Market overview ——
export const getIndices = () => request("/indices");
export const getTrending = (exchange = "NSE") => request(`/trending${qs({ exchange })}`);
export const getNews = (page = 1, size = 10) => request(`/news${qs({ page_no: page, size })}`);
export const getCommodities = () => request("/commodities");
export const getNseMostActive = () => request("/NSE_most_active");
export const getBseMostActive = () => request("/BSE_most_active");
export const getPriceShockers = () => request("/price_shockers");
export const get52WeekHighLow = () => request("/fetch_52_week_high_low_data");

// —— IPO & funds ——
export const getIpo = () => request("/ipo");
export const getMutualFunds = () => request("/mutual_funds");

// —— Search & company ——
export const searchStock = (query) => request(`/industry_search${qs({ query })}`);
export const searchIndustry = (query) => request(`/industry_search${qs({ query })}`);
export const searchMutualFund = (query) => request(`/mutual_fund_search${qs({ query })}`);
export const getStock = (name) => request(`/stock${qs({ name })}`);
export const getQuote = (symbol) => request(`/quote${qs({ symbol })}`);
export const getCorporateActions = (params) => request(`/corporate_actions${qs(params)}`);
export const getRecentAnnouncements = () => request("/recent_announcements");
