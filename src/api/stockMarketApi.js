import { API_ORIGIN } from "../config";

const DIRECT_BASE = "http://65.0.104.9";

function resolveBase() {
  const origin = API_ORIGIN || import.meta.env.VITE_API_URL || "";
  if (origin) return `${String(origin).replace(/\/+$/, "")}/api/market`;
  if (import.meta.env.DEV) return "/api/market";
  return `${DIRECT_BASE}`;
}

async function request(path) {
  const base = resolveBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.status === "error") {
    throw new Error(data.message || `Request failed (${res.status})`);
  }
  return data;
}

export const searchStocks = (query) =>
  request(`/search?q=${encodeURIComponent(query)}`);

export const getStock = (symbol, res = "num") =>
  request(`/stock?symbol=${encodeURIComponent(symbol)}&res=${res}`);

export const getStockList = (symbols, res = "num") =>
  request(`/stock/list?symbols=${encodeURIComponent(symbols.join(","))}&res=${res}`);

export const getSymbols = () => request("/symbols");
