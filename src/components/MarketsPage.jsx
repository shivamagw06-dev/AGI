// src/components/MarketsDashboard.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  RadialBarChart,
  RadialBar,
} from "recharts";
import { FiSearch, FiRefreshCw, FiDownload, FiChevronDown, FiClipboard, FiChevronRight } from "react-icons/fi";
import jsPDF from "jspdf";

/* ---------------------- CONFIG ---------------------- */
const DEBUG = false;
const API_ORIGIN =
  (typeof process !== "undefined" && process.env && process.env.REACT_APP_API_ORIGIN) ||
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_URL) ||
  "";

const SNAPSHOT_CACHE_KEY = "agimkt_snapshot_v2";
const RECENT_COMPANIES_KEY = "agimkt_recent_companies_v2";
const AUTO_REFRESH_MS = 2 * 60 * 60 * 1000;
const DEFAULT_LIVE_POLL_MS = 15 * 1000;

/* ---------------------- HELPERS ---------------------- */
function buildUrl(path, params = {}) {
  const base = API_ORIGIN ? API_ORIGIN.replace(/\/+$/, "") : "";
  const cleaned = path.startsWith("/") ? path : `/${path}`;
  const full = base ? `${base}${cleaned}` : cleaned;
  const url = new URL(full, typeof window !== "undefined" ? window.location.origin : "http://localhost");
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  });
  return url.toString();
}

async function fetchWithRetry(url, options = {}, attempts = 3, baseDelay = 400) {
  let i = 0;
  while (i < attempts) {
    try {
      const res = await fetch(url, options);
      const text = await res.text().catch(() => "");
      const ct = (res.headers && res.headers.get && res.headers.get("content-type")) || "";
      if (!res.ok) {
        if (ct.includes("json")) {
          try {
            const j = JSON.parse(text);
            throw new Error(j.error || j.message || `${res.status} ${res.statusText}`);
          } catch {
            throw new Error(`${res.status} ${res.statusText}: ${text}`);
          }
        }
        throw new Error(`${res.status} ${res.statusText}: ${text}`);
      }
      if (ct.includes("json")) {
        try {
          return JSON.parse(text);
        } catch {
          return text;
        }
      }
      return text;
    } catch (err) {
      i++;
      if (i >= attempts) throw err;
      const delay = baseDelay * 2 ** (i - 1) + Math.round(Math.random() * 200);
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, delay));
    }
  }
}

async function apiGet(path, params = {}) {
  const url = buildUrl(path, params);
  return fetchWithRetry(url, { headers: { Accept: "application/json" } }, 4, 300);
}

const fmtNumber = (v) => {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return new Intl.NumberFormat().format(n);
};
const fmtPct = (v) => {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
};
const clamp = (s, n = 180) => (s ? (String(s).length > n ? `${String(s).slice(0, n)}…` : s) : "—");

/* ---------------------- SMALL UI ---------------------- */
const Card = ({ children, className = "" }) => (
  <div className={`bg-white rounded-2xl shadow border p-4 ${className}`}>{children}</div>
);

const Stat = ({ label, value }) => (
  <div>
    <div className="text-xs text-gray-500">{label}</div>
    <div className="text-lg font-semibold text-slate-800">{value}</div>
  </div>
);

const Loading = ({ text = "Loading..." }) => (
  <div className="flex items-center gap-2 text-sm text-gray-500">
    <div className="w-4 h-4 border-2 border-current rounded-full animate-spin border-r-transparent" />
    <span>{text}</span>
  </div>
);

/* ---------------------- JSON MODAL ---------------------- */
function JsonModal({ open, title, data, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black opacity-40" onClick={onClose} />
      <div className="relative bg-white rounded-lg max-w-4xl w-full max-h-[85vh] overflow-auto p-4 shadow-lg">
        <div className="flex items-center justify-between mb-3">
          <div className="text-lg font-semibold">{title}</div>
          <div className="flex items-center gap-2">
            <button
              className="text-xs text-slate-500"
              onClick={() => {
                try {
                  navigator.clipboard.writeText(JSON.stringify(data || {}, null, 2));
                } catch {}
              }}
            >
              <FiClipboard className="inline mr-1" /> Copy
            </button>
            <button className="text-xs text-slate-500" onClick={onClose}>Close</button>
          </div>
        </div>
        <pre className="text-xs whitespace-pre-wrap" style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace" }}>
          {JSON.stringify(data || {}, null, 2)}
        </pre>
      </div>
    </div>
  );
}

/* ---------------------- READABLE VALUE HELPERS ---------------------- */
/**
 * Convert arbitrary metric value to a readable JSX.
 * - numbers -> formatted number
 * - arrays -> quick preview (first 3 entries) and count
 * - objects -> show common fields (displayName/value) or truncated JSON
 */
function renderValueReadable(v) {
  if (v === null || v === undefined || v === "") return <span className="text-slate-400">—</span>;

  // numbers
  if (typeof v === "number") return <span className="font-medium">{fmtNumber(v)}</span>;

  // strings that look like numbers
  const asNum = Number(v);
  if (!Number.isNaN(asNum) && String(v).trim() !== "") {
    return <span className="font-medium">{fmtNumber(asNum)}</span>;
  }

  // arrays
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="text-slate-400">[]</span>;
    // if array of primitives
    if (v.every((x) => typeof x !== "object")) {
      const preview = v.slice(0, 6).join(", ");
      return <span className="font-medium">{preview}{v.length > 6 ? ` … (+${v.length - 6})` : ""}</span>;
    }
    // array of objects -> try to extract displayName/value fields
    const items = v.slice(0, 3).map((it, i) => {
      if (!it) return null;
      if (typeof it === "object") {
        const label = it.displayName || it.name || it.metric || it.key || it.label || Object.keys(it)[0];
        const value = it.value ?? it.val ?? it.v ?? it.amount ?? it.y ?? it[Object.keys(it)[1]] ?? null;
        return (
          <div key={i} className="text-xs">
            <span className="text-slate-500">{label}: </span>
            <span className="font-medium">{value !== null && value !== undefined ? (typeof value === "number" ? fmtNumber(value) : String(value)) : clamp(JSON.stringify(it), 60)}</span>
          </div>
        );
      }
      return <div key={i} className="text-xs">{String(it)}</div>;
    });
    return <div>{items}{v.length > 3 && <div className="text-xs text-slate-400">+{v.length - 3} more</div>}</div>;
  }

  // objects
  if (typeof v === "object") {
    // common simple shape: { displayName: '...', value: 123 }
    if ("displayName" in v || "display_name" in v || "key" in v || "value" in v || "val" in v) {
      const label = v.displayName || v.display_name || v.key || Object.keys(v)[0];
      const value = v.value ?? v.val ?? v.amount ?? v.y ?? v[Object.keys(v)[1]] ?? null;
      return (
        <div>
          <div className="text-xs text-slate-500">{label}</div>
          <div className="font-medium">{value !== null && value !== undefined ? (typeof value === "number" ? fmtNumber(value) : String(value)) : clamp(JSON.stringify(v), 80)}</div>
        </div>
      );
    }
    // fallback: show up to first 3 key: value pairs
    const keys = Object.keys(v).slice(0, 6);
    return (
      <div>
        {keys.map((k) => {
          const val = v[k];
          return (
            <div key={k} className="text-xs flex justify-between">
              <div className="text-slate-500 pr-2">{k}</div>
              <div className="font-medium">{typeof val === "number" ? fmtNumber(val) : (typeof val === "string" ? (val.length > 60 ? `${val.slice(0, 60)}…` : val) : clamp(JSON.stringify(val), 60))}</div>
            </div>
          );
        })}
        {Object.keys(v).length > 6 && <div className="text-xs text-slate-400">+{Object.keys(v).length - 6} more</div>}
      </div>
    );
  }

  // strings
  return <span className="font-medium">{String(v).length > 100 ? `${String(v).slice(0, 100)}…` : String(v)}</span>;
}

/* ---------------------- UI PRIMITIVES ---------------------- */

function copyToClipboard(text) {
  try {
    navigator.clipboard.writeText(text);
  } catch {
    // fallback
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
}

const KVRow = ({ label, value, className = "" }) => (
  <div className={`flex items-start gap-3 ${className}`}>
    <div className="w-36 text-xs text-slate-500">{label}</div>
    <div className="flex-1 text-sm">{renderValueReadable(value)}</div>
  </div>
);

function CollapsibleList({ label, items, previewItems = 3 }) {
  const [open, setOpen] = useState(false);
  if (!items) return null;
  if (!Array.isArray(items) && typeof items === "object") {
    // show object as collapse with key/value rows
    const keys = Object.keys(items).slice(0, 12);
    return (
      <div>
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setOpen((s) => !s)}>
          <div className="text-sm font-semibold">{label}</div>
          <div className="text-xs text-indigo-600">{open ? "Hide" : `Show ${keys.length}`}</div>
        </div>
        {open && (
          <div className="mt-2 space-y-1">
            {keys.map((k) => (
              <div key={k} className="flex justify-between text-xs border-b py-1">
                <div className="text-slate-600">{k}</div>
                <div className="font-medium">{renderValueReadable(items[k])}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  if (!Array.isArray(items)) return null;
  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">{label}</div>
        <div className="flex items-center gap-2">
          <div className="text-xs text-slate-400">{items.length} items</div>
          <button className="text-xs text-indigo-600" onClick={() => setOpen((s) => !s)}>{open ? "Collapse" : `Expand`}</button>
        </div>
      </div>
      <div className="mt-2 space-y-1">
        {items.slice(0, previewItems).map((it, i) => (
          <div key={i} className="flex justify-between items-start gap-3 text-xs p-2 bg-slate-50 rounded">
            <div className="flex-1">{typeof it === "object" ? (it.displayName || it.name || JSON.stringify(it).slice(0, 80)) : String(it)}</div>
            <div className="text-slate-600">{typeof it === "object" ? (it.value ?? it.val ?? "") : ""}</div>
          </div>
        ))}
        {items.length > previewItems && !open && <div className="text-xs text-slate-400">… {items.length - previewItems} more</div>}
        {open && items.slice(previewItems).map((it, i) => (
          <div key={`more-${i}`} className="flex justify-between items-start gap-3 text-xs p-2 border rounded">
            <div className="flex-1">{typeof it === "object" ? (it.displayName || it.name || JSON.stringify(it).slice(0, 120)) : String(it)}</div>
            <div className="text-slate-600">{typeof it === "object" ? (it.value ?? it.val ?? "") : ""}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InfoSection({ title, rightAction, children, badge }) {
  return (
    <div className="bg-white rounded-2xl shadow border p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          {badge && <div className="text-xs text-slate-400 mt-1">{badge}</div>}
        </div>
        <div>{rightAction}</div>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

/* ---------------------- other helpers (unchanged) ---------------------- */
function buildSeriesFromTechnical(stockTechnicalData, key) {
  if (!stockTechnicalData) return [];
  const candidate = stockTechnicalData[key] || stockTechnicalData[key.toLowerCase()] || stockTechnicalData[key.toUpperCase()] || (stockTechnicalData.indicators && (stockTechnicalData.indicators[key] || stockTechnicalData.indicators[key.toUpperCase()]));
  if (!candidate) return [];
  if (Array.isArray(candidate)) {
    if (candidate.length && typeof candidate[0] === "object" && ("value" in candidate[0] || "v" in candidate[0] || "y" in candidate[0])) {
      return candidate.map((d) => ({ date: d.ts || d.time || d.date || d.t || d[0], value: Number(d.value ?? d.v ?? d.y ?? d[1] ?? d.v ?? NaN) }));
    }
    if (candidate.length && Array.isArray(candidate[0]) && candidate[0].length >= 2) {
      return candidate.map((p) => ({ date: p[0], value: Number(p[1]) }));
    }
  } else if (typeof candidate === "object") {
    const v = candidate.values || candidate.series || candidate.data || candidate.points;
    if (Array.isArray(v)) {
      if (v.length && Array.isArray(v[0]) && v[0].length >= 2) return v.map((p) => ({ date: p[0], value: Number(p[1]) }));
      if (v.length && typeof v[0] === "object" && ("value" in v[0] || "y" in v[0])) {
        return v.map((d) => ({ date: d.ts || d.time || d.date || d[0], value: Number(d.value ?? d.y ?? d[1] ?? NaN) }));
      }
    }
    return Object.entries(candidate).map(([k, v2]) => ({ date: k, value: Number(v2) }));
  }
  return [];
}

/* ---------------------- MAIN ---------------------- */
export default function MarketsDashboard() {
  /* ---------------------- existing state & refs (kept intact) ---------------------- */
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [trending, setTrending] = useState(null);
  const [nseActive, setNseActive] = useState([]);
  const [bseActive, setBseActive] = useState([]);
  const [week52, setWeek52] = useState(null);
  const [mutualFunds, setMutualFunds] = useState(null);
  const [priceShockers, setPriceShockers] = useState([]);
  const [commodities, setCommodities] = useState([]);

  const [query, setQuery] = useState("TCS");
  const [company, setCompany] = useState(null);
  const [historical, setHistorical] = useState(null);
  const [priceTarget, setPriceTarget] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [historicalStats, setHistoricalStats] = useState(null);

  const [deepDive, setDeepDive] = useState(null);

  const [industryQuery, setIndustryQuery] = useState("");
  const [industryResults, setIndustryResults] = useState([]);
  const [mfQuery, setMfQuery] = useState("");
  const [mfResults, setMfResults] = useState([]);

  const [loadingCompany, setLoadingCompany] = useState(false);
  const [error, setError] = useState(null);
  const [serverErrorCount, setServerErrorCount] = useState(0);
  const [showRecSnapshots, setShowRecSnapshots] = useState(false);

  // autocomplete
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);

  // modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState("");
  const [modalData, setModalData] = useState(null);

  const refreshTimer = useRef(null);
  const livePollTimer = useRef(null);
  const livePollTicker = useRef(null);
  const livePollIntervalMs = useRef(DEFAULT_LIVE_POLL_MS);
  const suggestionDebounce = useRef(null);

  /* ------------------ cache helpers (unchanged) ------------------ */
  function saveSnapshotCache(snapshot) {
    try {
      localStorage.setItem(SNAPSHOT_CACHE_KEY, JSON.stringify({ ts: Date.now(), data: snapshot }));
    } catch {}
  }
  function loadSnapshotCache() {
    try {
      const raw = localStorage.getItem(SNAPSHOT_CACHE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (Date.now() - (parsed.ts || 0) > 10 * 60 * 1000) return parsed.data;
      return parsed.data;
    } catch {
      return null;
    }
  }
  function saveRecentCompany(name, payload) {
    try {
      const raw = JSON.parse(localStorage.getItem(RECENT_COMPANIES_KEY) || "[]");
      const filtered = raw.filter((r) => r.name !== name);
      filtered.unshift({ name, ts: Date.now(), payload });
      localStorage.setItem(RECENT_COMPANIES_KEY, JSON.stringify(filtered.slice(0, 8)));
    } catch {}
  }
  function loadRecentCompanies() {
    try {
      return JSON.parse(localStorage.getItem(RECENT_COMPANIES_KEY) || "[]");
    } catch {
      return [];
    }
  }

  /* ------------------ research helper (unchanged) ------------------ */
  async function fetchResearchSummary(ticker, mode = "short") {
    const candidates = [
      "/research/summary",
      "/api/research/summary",
      buildUrl("/research/summary"),
    ].filter(Boolean);

    const tryPost = async (url) => {
      return fetchWithRetry(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ ticker, mode }),
      }, 2, 300);
    };

    let lastErr = null;
    for (const url of candidates) {
      try {
        const r = await tryPost(url);
        if (r) return r;
      } catch (err) {
        lastErr = err;
      }
    }
    console.warn("research fetch failed (all candidates):", lastErr);
    return null;
  }

  /* ------------------ live quote poll helpers (unchanged) ------------------ */
  function stopLivePoll() {
    if (livePollTimer.current) {
      clearInterval(livePollTimer.current);
      livePollTimer.current = null;
    }
    livePollTicker.current = null;
  }

  async function pollLiveQuote(ticker) {
    if (!ticker) return;
    try {
      const q = await apiGet("/api/quote", { symbol: ticker });
      if (!q) return;

      const raw = q.raw || null;
      const cp =
        q.currentPrice ||
        q.current_price ||
        q.price ||
        q.last_price ||
        q.lastTradedPrice ||
        q.last_traded_price ||
        (raw && (raw.price || raw.last_price || raw.lastPrice)) ||
        null;
      const percent =
        q.percentChange ??
        q.changePercent ??
        q.percent_change ??
        q.percent ??
        q.change ??
        (raw && (raw.percentChange ?? raw.change ?? raw.percent)) ??
        null;
      const volume = q.volume ?? q.totalVolume ?? q.v ?? (raw && (raw.volume || raw.totalVolume || raw.v)) ?? null;
      const prevClose =
        q.prevClose ?? q.previous_close ?? q.prev_close ?? (raw && (raw.prevClose || raw.previous_close || raw.prev_close)) ?? null;
      const openPrice = q.openPrice ?? q.open ?? (raw && (raw.open || raw.openPrice)) ?? null;
      const dayRange = q.dayRange ?? (q.low && q.high ? { low: q.low, high: q.high } : null) ?? (raw && raw.dayRange) ?? null;

      setCompany((prev) => {
        if (!prev) return prev;
        const updated = { ...prev };
        updated.currentPrice = cp || updated.currentPrice;
        updated.percentChange = percent ?? updated.percentChange;
        updated.stockDetailsReusableData = {
          ...(updated.stockDetailsReusableData || {}),
          volume: volume ?? (updated.stockDetailsReusableData || {}).volume,
          prevClose: prevClose ?? (updated.stockDetailsReusableData || {}).prevClose,
          openPrice: openPrice ?? (updated.stockDetailsReusableData || {}).openPrice,
        };
        if (dayRange) {
          updated.dayRange = dayRange;
        }
        return updated;
      });
      setServerErrorCount(0);
    } catch (e) {
      console.warn("live quote poll failed", e);
      setServerErrorCount((c) => c + 1);
    }
  }

  function startLivePoll(ticker, intervalMs = DEFAULT_LIVE_POLL_MS) {
    if (!ticker) return;
    if (livePollTicker.current && String(livePollTicker.current).toLowerCase() === String(ticker).toLowerCase()) return;
    stopLivePoll();
    livePollTicker.current = ticker;
    livePollIntervalMs.current = intervalMs;
    pollLiveQuote(ticker).catch(() => {});
    livePollTimer.current = setInterval(() => {
      pollLiveQuote(ticker).catch(() => {});
    }, intervalMs);
  }

  /* ------------------ load snapshot (unchanged) ------------------ */
  async function loadSnapshot(useCache = true) {
    setSnapshotLoading(true);
    setError(null);
    try {
      const cached = useCache ? loadSnapshotCache() : null;
      if (cached) {
        setTrending(cached.trending || null);
        setNseActive(cached.nseActive || []);
        setBseActive(cached.bseActive || []);
        setWeek52(cached.week52 || null);
        setMutualFunds(cached.mutualFunds || null);
        setPriceShockers(cached.priceShockers || []);
        setCommodities(cached.commodities || []);
      }

      const [
        trRes,
        nseRes,
        bseRes,
        week52Res,
        mfRes,
        shockersRes,
        commRes,
      ] = await Promise.allSettled([
        apiGet("/api/trending"),
        apiGet("/api/NSE_most_active"),
        apiGet("/api/BSE_most_active"),
        apiGet("/api/fetch_52_week_high_low_data"),
        apiGet("/api/mutual_funds"),
        apiGet("/api/price_shockers"),
        apiGet("/api/commodities"),
      ]);

      let researchCom = null;
      try {
        researchCom = await fetchResearchSummary("market_snapshot", "short");
      } catch (e) {
        researchCom = null;
      }

      const snapshot = {
        trending: trRes.status === "fulfilled" ? (trRes.value.trending_stocks || trRes.value) : null,
        nseActive: nseRes.status === "fulfilled" ? (Array.isArray(nseRes.value) ? nseRes.value : nseRes.value || []) : [],
        bseActive: bseRes.status === "fulfilled" ? (Array.isArray(bseRes.value) ? bseRes.value : bseRes.value || []) : [],
        week52: week52Res.status === "fulfilled" ? week52Res.value : null,
        mutualFunds: mfRes.status === "fulfilled" ? mfRes.value : null,
        priceShockers: shockersRes.status === "fulfilled" ? shockersRes.value || [] : [],
        commodities:
          (researchCom && researchCom.source_data && Array.isArray(researchCom.source_data.commodities) && researchCom.source_data.commodities.length)
            ? researchCom.source_data.commodities
            : (commRes.status === "fulfilled" ? commRes.value || [] : []),
      };

      setTrending(snapshot.trending);
      setNseActive(snapshot.nseActive);
      setBseActive(snapshot.bseActive);
      setWeek52(snapshot.week52);
      setMutualFunds(snapshot.mutualFunds);
      setPriceShockers(snapshot.priceShockers);
      setCommodities(snapshot.commodities);

      saveSnapshotCache(snapshot);
      setServerErrorCount(0);
    } catch (e) {
      console.error("snapshot error", e);
      setError(String(e));
      setServerErrorCount((c) => c + 1);
    } finally {
      setSnapshotLoading(false);
    }
  }

  /* ------------------ load company (unchanged) ------------------ */
  async function loadCompany(name) {
    if (!name) return;
    setLoadingCompany(true);
    setError(null);
    setCompany(null);
    setHistorical(null);
    setPriceTarget(null);
    setForecast(null);
    setHistoricalStats(null);
    setDeepDive(null);

    stopLivePoll();

    try {
      const research = await fetchResearchSummary(name, "short");
      if (DEBUG) console.debug("research payload for", name, research);

      if (research && research.source_data && research.source_data.stockData) {
        const sd = research.source_data.stockData || {};
        const rawFromSd = sd.raw || sd.rawData || sd.source || sd.original || null;

        const normalized = {
          tickerId: sd.tickerId || sd.ticker || sd.ticker_id || sd.symbol || (rawFromSd && (rawFromSd.symbol || rawFromSd.ticker)) || name,
          companyName:
            sd.companyName || sd.commonName || sd.name || sd.company_name || sd.company || sd.tickerName || (rawFromSd && rawFromSd.name) || name,
          industry:
            sd.industry || sd.sector || sd.industrySector || (rawFromSd && rawFromSd.sector) || null,
          companyProfile:
            sd.companyProfile || sd.company_profile || sd.profile || sd.description || (rawFromSd && rawFromSd.profile) || {},
          currentPrice:
            sd.currentPrice ||
            sd.current_price ||
            (sd.last_price ? (typeof sd.last_price === "object" ? sd.last_price : { NSE: sd.last_price, BSE: sd.last_price }) : null) ||
            (rawFromSd && (rawFromSd.currentPrice || rawFromSd.price || rawFromSd.last_price || rawFromSd.lastPrice)) ||
            null,
          stockTechnicalData:
            sd.stockTechnicalData || sd.stock_technical_data || (rawFromSd && rawFromSd.stockTechnicalData) || null,
          percentChange:
            sd.percentChange ?? sd.changePercent ?? sd.percent_change ?? sd.change ?? (rawFromSd && (rawFromSd.percentChange ?? rawFromSd.change ?? rawFromSd.percent)) ?? null,
          yearHigh: sd.yearHigh ?? sd.high52 ?? sd._52WeekHigh ?? (rawFromSd && (rawFromSd.high52 || rawFromSd.yearHigh)) ?? null,
          yearLow: sd.yearLow ?? sd.low52 ?? sd._52WeekLow ?? (rawFromSd && (rawFromSd.low52 ?? rawFromSd.yearLow)) ?? null,
          financials: sd.financials || sd.financial_data || rawFromSd?.financials || null,
          keyMetrics: sd.keyMetrics || sd.key_metrics || sd.metrics || rawFromSd?.keyMetrics || null,
          futureExpiryDates: sd.futureExpiryDates || sd.future_expiry_dates || sd.future_dates || (rawFromSd && rawFromSd.futureExpiryDates) || [],
          futureOverviewData: sd.futureOverviewData || sd.future_overview || (rawFromSd && rawFromSd.futureOverviewData) || null,
          initialStockFinancialData: sd.initialStockFinancialData || sd.initial_stock_financial_data || null,
          analystView: sd.analystView || sd.analyst_view || null,
          recosBar: sd.recosBar || sd.recommendationBar || null,
          riskMeter: sd.riskMeter || sd.risk_meter || null,
          shareholding: sd.shareholding || sd.share_holding || sd.shareholdingPattern || null,
          stockCorporateActionData: sd.stockCorporateActionData || sd.corporateActions || null,
          stockDetailsReusableData:
            sd.stockDetailsReusableData ||
            sd.stock_details_reusable_data ||
            (rawFromSd && rawFromSd.stockDetailsReusableData) ||
            {
              marketCap: sd.marketCap || sd.market_cap || sd.marketCapitalization || sd.marketCapital || (rawFromSd && rawFromSd.market_cap) || null,
              peRatio: sd.peRatio || sd.pe || sd.p_e_ratio || sd.pe_ratio || sd.pe_ratio || (rawFromSd && (rawFromSd.pe || rawFromSd.pe_ratio)) || null,
              eps: sd.eps || sd.EPS || sd.e_p_s || (rawFromSd && (rawFromSd.eps || rawFromSd.EPS)) || null,
              dividendYield: sd.dividendYield || sd.dividend_yield || sd.div_yield || (rawFromSd && rawFromSd.dividendYield) || null,
              volume: sd.volume ?? sd.last_traded_volume ?? sd.avgVolume ?? (rawFromSd && (rawFromSd.volume || rawFromSd.avgVolume)) ?? null,
              prevClose: sd.prevClose ?? sd.previous_close ?? sd.prev_close ?? (rawFromSd && (rawFromSd.prevClose || rawFromSd.previous_close)) ?? null,
            },
          recentNews: sd.recentNews || sd.recent_news || rawFromSd?.recentNews || [],
        };

        if (typeof normalized.currentPrice === "number") {
          normalized.currentPrice = { NSE: normalized.currentPrice, BSE: normalized.currentPrice };
        }

        setCompany(normalized);
        setDeepDive(research);

        if (research.source_data.priceTarget) setPriceTarget(research.source_data.priceTarget);

        if (research.source_data.historical && Array.isArray(research.source_data.historical) && research.source_data.historical.length) {
          setHistorical(research.source_data.historical);
        } else {
          try {
            const hist = await apiGet("/api/historical_data", { symbol: name, period: "1yr", filter: "price" });
            if (DEBUG) console.debug("/api/historical_data payload for", name, hist);
            setHistorical(hist?.datasets || hist || null);
          } catch (e) {
            setHistorical(null);
          }
        }

        if (research.source_data.commodities && Array.isArray(research.source_data.commodities) && research.source_data.commodities.length) {
          setCommodities(research.source_data.commodities);
        }

        saveRecentCompany(name, normalized);

        const ticker = normalized.tickerId || name;
        startLivePoll(ticker, DEFAULT_LIVE_POLL_MS);
      } else {
        // fallback to /api/stock which returns the structured object described by you
        const stock = await apiGet("/api/stock", { name });
        if (DEBUG) console.debug("/api/stock payload for", name, stock);

        const mapped = stock
          ? {
              tickerId: stock.tickerId || stock.ticker || stock.ticker_id || stock.symbol || name,
              companyName: stock.companyName || stock.company_name || stock.name || name,
              industry: stock.industry || stock.sector || null,
              companyProfile: stock.companyProfile || stock.company_profile || stock.profile || stock.description || {},
              currentPrice: stock.currentPrice || stock.current_price || stock.price || null,
              stockTechnicalData: stock.stockTechnicalData || stock.stock_technical_data || null,
              percentChange: stock.percentChange ?? stock.changePercent ?? stock.percent_change ?? stock.change ?? null,
              yearHigh: stock.yearHigh ?? stock.high52 ?? stock._52WeekHigh ?? null,
              yearLow: stock.yearLow ?? stock.low52 ?? stock._52WeekLow ?? null,
              financials: stock.financials || stock.financialData || null,
              keyMetrics: stock.keyMetrics || stock.key_metrics || stock.metrics || null,
              futureExpiryDates: stock.futureExpiryDates || stock.future_expiry_dates || stock.future_dates || [],
              futureOverviewData: stock.futureOverviewData || stock.future_overview || null,
              initialStockFinancialData: stock.initialStockFinancialData || null,
              analystView: stock.analystView || stock.analyst_view || null,
              recosBar: stock.recosBar || stock.recommendationBar || null,
              riskMeter: stock.riskMeter || stock.risk_meter || null,
              shareholding: stock.shareholding || stock.share_holding || stock.shareholdingPattern || null,
              stockCorporateActionData: stock.stockCorporateActionData || stock.corporateActions || null,
              stockDetailsReusableData: stock.stockDetailsReusableData || stock.stockDetails || {},
              recentNews: stock.recentNews || stock.recent_news || [],
            }
          : null;

        setCompany(mapped || stock || null);
        saveRecentCompany(name, mapped || stock || null);

        const ticker = mapped?.tickerId || mapped?.ticker || name;

        try {
          const hist = await apiGet("/api/historical_data", { symbol: name, period: "1yr", filter: "price" });
          if (DEBUG) console.debug("/api/historical_data payload for", name, hist);
          setHistorical(hist?.datasets || hist || null);
        } catch {
          setHistorical(null);
        }

        try {
          const pt = await apiGet("/api/stock_target_price", { stock_id: ticker });
          if (DEBUG) console.debug("/api/stock_target_price payload for", ticker, pt);
          setPriceTarget(pt || null);
        } catch {
          setPriceTarget(null);
        }

        try {
          const fc = await apiGet("/api/stock_forecasts", { stock_id: ticker, measure_code: "EPS", period_type: "Annual", data_type: "Estimates", age: "Current" });
          if (DEBUG) console.debug("/api/stock_forecasts payload for", ticker, fc);
          setForecast(fc || null);
        } catch {
          setForecast(null);
        }

        try {
          const hs = await apiGet("/api/historical_stats", { stock_name: name, stats: "quarter_results" });
          if (DEBUG) console.debug("/api/historical_stats payload for", name, hs);
          setHistoricalStats(hs || null);
        } catch {
          setHistoricalStats(null);
        }

        startLivePoll(ticker, DEFAULT_LIVE_POLL_MS);
      }

      setServerErrorCount(0);
    } catch (e) {
      console.error("company fetch error", e);
      setError(String(e));
      setServerErrorCount((c) => c + 1);
      const recents = loadRecentCompanies();
      const r = recents.find((x) => x.name.toLowerCase() === name.toLowerCase());
      if (r) setCompany(r.payload || null);
    } finally {
      setLoadingCompany(false);
      setSuggestionsOpen(false);
    }
  }

  /* ------------------ SEARCH / AUTOCOMPLETE HELPERS (unchanged) ------------------ */
  async function fetchSuggestionsFromServer(q) {
    const suggestionCandidates = [
      { path: "/api/stock_search", paramName: "query" },
      { path: "/api/search", paramName: "query" },
      { path: "/api/stock", paramName: "name" },
      { path: "/api/industry_search", paramName: "query" },
    ];

    for (const cand of suggestionCandidates) {
      try {
        const res = await apiGet(cand.path, { [cand.paramName]: q });
        if (!res) continue;
        if (Array.isArray(res)) {
          const norm = res.map((r) => ({
            label: r.company || r.companyName || r.schemeName || r.commonName || r.name || r.ticker || r.ticker_id || r.isin || String(r),
            ticker: r.ticker || r.ticker_id || r.symbol || r.tickerId || null,
            payload: r,
            source: cand.path,
          }));
          if (norm.length) return norm;
        }
        if (res.data && Array.isArray(res.data)) {
          const norm = res.data.map((r) => ({
            label: r.company || r.companyName || r.commonName || r.name || r.ticker || r.ticker_id || r.isin || String(r),
            ticker: r.ticker || r.ticker_id || r.symbol || r.tickerId || null,
            payload: r,
            source: cand.path,
          }));
          if (norm.length) return norm;
        }
        if (res && typeof res === "object" && (res.company || res.companyName || res.ticker || res.tickerId)) {
          return [{
            label: res.company || res.companyName || res.commonName || res.name || res.ticker || res.tickerId,
            ticker: res.ticker || res.tickerId || null,
            payload: res,
            source: cand.path,
          }];
        }
      } catch (e) {
        if (DEBUG) console.debug("suggestion candidate failed", cand.path, e);
      }
    }
    return [];
  }

  async function loadSuggestions(q) {
    if (!q || String(q).trim().length < 1) {
      setSuggestions([]);
      setSuggestionsOpen(false);
      return;
    }
    setLoadingSuggestions(true);
    setActiveSuggestionIndex(-1);

    try {
      const recents = loadRecentCompanies().filter((r) => r.name.toLowerCase().includes(q.toLowerCase())).map((r) => ({
        label: r.name,
        ticker: r.payload?.tickerId || r.payload?.ticker || null,
        payload: r.payload,
        source: "recent",
      }));

      const snapCandidates = (trending && (trending.top_gainers || trending.topGainers || trending)) || [];
      const snapMatches = (snapCandidates || [])
        .filter((s) => (s.company || s.company_name || s.ticker || "").toLowerCase().includes(q.toLowerCase()))
        .map((s) => ({
          label: s.company || s.company_name || s.ticker,
          ticker: s.ticker || s.ticker_id || null,
          payload: s,
          source: "snapshot",
        }));

      const seen = new Set();
      const combined = [];
      for (const s of [...recents, ...snapMatches]) {
        const key = (s.label || s.ticker || "").toLowerCase();
        if (!seen.has(key)) {
          combined.push(s);
          seen.add(key);
        }
      }

      if (combined.length) {
        setSuggestions(combined.slice(0, 8));
        setSuggestionsOpen(true);
      }

      const serverSug = await fetchSuggestionsFromServer(q);
      const merged = [...combined];
      for (const s of serverSug) {
        const key = (s.label || s.ticker || "").toLowerCase();
        if (!seen.has(key)) {
          merged.push(s);
          seen.add(key);
        }
      }

      setSuggestions(merged.slice(0, 12));
      setSuggestionsOpen(merged.length > 0);
    } catch (e) {
      console.error("suggestions fail", e);
      setSuggestions([]);
      setSuggestionsOpen(false);
    } finally {
      setLoadingSuggestions(false);
    }
  }

  function scheduleSuggestions(q) {
    if (suggestionDebounce.current) clearTimeout(suggestionDebounce.current);
    suggestionDebounce.current = setTimeout(() => {
      loadSuggestions(q).catch(() => {});
    }, 300);
  }

  /* ------------------ search helpers (unchanged) ------------------ */
  async function doIndustrySearch(q) {
    if (!q) return setIndustryResults([]);
    try {
      const res = await apiGet("/api/industry_search", { query: q });
      setIndustryResults(Array.isArray(res) ? res : res.data || []);
    } catch (e) {
      console.error("industry search fail", e);
      setIndustryResults([]);
    }
  }
  async function doMfSearch(q) {
    if (!q) return setMfResults([]);
    try {
      const res = await apiGet("/api/mutual_fund_search", { query: q });
      setMfResults(Array.isArray(res) ? res : res.data || []);
    } catch (e) {
      console.error("mf search fail", e);
      setMfResults([]);
    }
  }

  useEffect(() => {
    loadSnapshot(true);
    refreshTimer.current = setInterval(() => loadSnapshot(false), AUTO_REFRESH_MS);
    const recents = loadRecentCompanies();
    const r = recents.find((x) => x.name.toLowerCase() === query.toLowerCase());
    if (r) setCompany(r.payload);

    return () => {
      clearInterval(refreshTimer.current);
      stopLivePoll();
      if (suggestionDebounce.current) clearTimeout(suggestionDebounce.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ------------------ derived values (unchanged) ------------------ */
  const topGainers = useMemo(() => {
    const t = trending?.top_gainers || trending?.topGainers || [];
    if (t && t.length) return t.slice(0, 6);
    const arr = (nseActive || []).map((a) => ({ company_name: a.company, ticker_id: a.ticker, price: a.price, percent_change: a.percent_change }));
    return arr.sort((a, b) => (Number(b.percent_change || 0) - Number(a.percent_change || 0))).slice(0, 6);
  }, [trending, nseActive]);

  const topLosers = useMemo(() => {
    const t = trending?.top_losers || trending?.topLosers || [];
    if (t && t.length) return t.slice(0, 6);
    const arr = (nseActive || []).map((a) => ({ company_name: a.company, ticker_id: a.ticker, price: a.price, percent_change: a.percent_change }));
    return arr.sort((a, b) => (Number(a.percent_change || 0) - Number(b.percent_change || 0))).slice(0, 6);
  }, [trending, nseActive]);

  const priceSetForChart = useMemo(() => {
    if (!historical) return [];
    const datasets = Array.isArray(historical) ? historical : (historical.datasets || []);
    const priceSet = datasets.find((d) => /price/i.test(d.metric || d.label || "")) || datasets[0];
    const values = priceSet?.values || [];
    return values.map((v) => ({ date: v[0], value: Number(v[1]) }));
  }, [historical]);

  const normalizedCommodities = useMemo(() => {
    return (commodities || []).map((c) => {
      return {
        id: c.contractId || c.contract_id || c.id || c.commoditySymbol || c.commodity_symbol || c.contractId || null,
        name: c.commoditySymbol || c.commodity_symbol || c.commodity || c.commodityName || c.contractId || c.id || "—",
        lastTradedPrice: c.lastTradedPrice ?? c.last_traded_price ?? c.lastPrice ?? c.last_price ?? null,
      };
    });
  }, [commodities]);

  const sectorTiles = useMemo(() => {
    const map = {};
    (industryResults || []).forEach((it) => {
      const sector = it.mgSector || it.mgIndustry || "Other";
      map[sector] = map[sector] || { count: 0, sumPct: 0, sourceCount: 0 };
      const rating = (it.activeStockTrends?.overallRating || "").toLowerCase();
      let approx = 0;
      if (rating.includes("bull")) approx = 1.5;
      if (rating.includes("bear")) approx = -1.5;
      if (rating.includes("neutral")) approx = 0;
      map[sector].count += 1;
      map[sector].sumPct += approx;
      map[sector].sourceCount += 1;
    });
    (nseActive || []).forEach((st) => {
      const sector = st.sector || st.mgSector || st.industry || "Other";
      map[sector] = map[sector] || { count: 0, sumPct: 0, sourceCount: 0 };
      const pct = Number(st.percent_change || st.percentChange || 0);
      map[sector].count += 1;
      map[sector].sumPct += pct;
      map[sector].sourceCount += 1;
    });

    return Object.entries(map).map(([sector, v]) => {
      const avgPct = v.sourceCount ? v.sumPct / v.sourceCount : 0;
      return { sector, count: v.count, avgPct };
    }).sort((a, b) => b.count - a.count);
  }, [industryResults, nseActive]);

  /* ------------------ export helpers (unchanged) ------------------ */
  function exportTableToCSV(rows, filename = "report.csv") {
    if (!rows || !rows.length) return;
    const header = Object.keys(rows[0]);
    const csv = [
      header.join(","),
      ...rows.map((r) => header.map((h) => {
        let cell = r[h] === null || r[h] === undefined ? "" : String(r[h]);
        if (cell.includes(",") || cell.includes('"') || cell.includes("\n")) cell = `"${cell.replace(/"/g, '""')}"`;
        return cell;
      }).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportReportPdf() {
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const margin = 40;
    let y = 40;
    doc.setFontSize(16);
    doc.text("Markets Dashboard Report", margin, y);
    y += 22;
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, margin, y);
    y += 18;

    if (company) {
      doc.setFontSize(12);
      doc.text(`Company: ${company.companyName || company.tickerId || query}`, margin, y);
      y += 16;
      doc.setFontSize(10);
      const cpText = company.currentPrice
        ? `${company.currentPrice.NSE ?? company.currentPrice?.nse ?? "—"} / ${company.currentPrice.BSE ?? company.currentPrice?.bse ?? "—"}`
        : "—";
      doc.text(`Price (NSE / BSE): ${cpText}`, margin, y);
      y += 12;
      doc.text(`Percent change: ${fmtPct(company.percentChange)}`, margin, y);
      y += 12;
      const sd = company.stockDetailsReusableData || {};
      doc.text(`P/E: ${fmtNumber(sd.peRatio ?? sd.pe ?? sd.PE) }  ·  EPS: ${fmtNumber(sd.eps ?? sd.EPS) }  ·  Dividend Yield: ${fmtNumber(sd.dividendYield ?? sd.dividend_yield)}`, margin, y);
      y += 18;
    }

    doc.setFontSize(11);
    doc.text("Top Gainers (sample)", margin, y);
    y += 14;
    const g = topGainers.slice(0, 6);
    g.forEach((row) => {
      if (y > 740) { doc.addPage(); y = 40; }
      doc.text(`${row.company_name || row.company || row.ticker || "-"}  —  ${fmtNumber(row.price)}  (${fmtPct(row.percent_change ?? row.percentChange)})`, margin, y);
      y += 12;
    });

    doc.save(`markets-report-${(company?.tickerId || query).toLowerCase()}.pdf`);
  }

  /* ------------------ PRICE TARGET helpers (unchanged) ------------------ */
  function getPriceTargetSummary(pt) {
    if (!pt || !pt.priceTarget) return null;
    const mean = pt.priceTarget.Mean ?? pt.priceTarget.UnverifiedMean ?? pt.priceTarget.PreliminaryMean ?? null;
    const median = pt.priceTarget.Median ?? null;
    const count = pt.priceTarget.NumberOfEstimates ?? pt.priceTarget.NumberOfRecommendations ?? null;
    let recentSnapshot = null;
    const snaps = pt.priceTargetSnapshots?.PriceTargetSnapshot || pt.priceTargetSnapshots || [];
    if (Array.isArray(snaps) && snaps.length) {
      const found = snaps.find((s) => s.Mean || s.UnverifiedMean) || snaps[0];
      recentSnapshot = {
        age: found.Age || found.age || "Snapshot",
        mean: found.Mean ?? found.UnverifiedMean ?? null,
      };
    }
    return { mean, median, count, recentSnapshot };
  }

  const priceTargetSummary = useMemo(() => getPriceTargetSummary(priceTarget), [priceTarget]);

  /* ------------------ AUTOCOMPLETE UI HANDLERS (unchanged) ------------------ */
  function onQueryChange(e) {
    const v = e.target.value;
    setQuery(v);
    scheduleSuggestions(v);
  }

  function onQueryKeyDown(e) {
    if (e.key === "Enter") {
      if (suggestionsOpen && activeSuggestionIndex >= 0 && suggestions[activeSuggestionIndex]) {
        const sel = suggestions[activeSuggestionIndex];
        setQuery(sel.label);
        setSuggestionsOpen(false);
        loadCompany(sel.label);
        return;
      }
      loadCompany(query);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!suggestionsOpen) {
        scheduleSuggestions(query);
        return;
      }
      setActiveSuggestionIndex((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveSuggestionIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Escape") {
      setSuggestionsOpen(false);
    }
  }

  function onSuggestionClick(s) {
    setQuery(s.label);
    setSuggestionsOpen(false);
    loadCompany(s.label);
  }

  /* ------------------ RENDER ------------------ */
  return (
    <div className="p-6 max-w-screen-6xl mx-auto">
      <JsonModal open={modalOpen} title={modalTitle} data={modalData} onClose={() => setModalOpen(false)} />

      <div className="flex items-start justify-between gap-6 mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Markets Dashboard</h1>
          <div className="mt-1 text-sm text-slate-500">
            Using backend: <span className="font-mono text-xs">{API_ORIGIN ? `${API_ORIGIN}/api/*` : "/api/* (same origin)"}</span>
          </div>
          {serverErrorCount > 0 && (
            <div className="mt-2 text-xs text-red-600">Server errors detected: {serverErrorCount}</div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => loadSnapshot(false)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-2">
            <FiRefreshCw /> Refresh
          </button>
          <button onClick={() => exportReportPdf()} className="px-4 py-2 bg-slate-50 border rounded-lg flex items-center gap-2">
            <FiDownload /> Export PDF
          </button>
        </div>
      </div>

      {/* search + summary (unchanged layout) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        <div className="lg:col-span-8">
          <Card>
            <div className="flex flex-col md:flex-row md:items-center gap-4">
              <div className="flex-1 relative">
                <label className="text-xs text-slate-500 mb-2 block">Company Search</label>
                <div className="flex gap-2">
                  <input
                    value={query}
                    onChange={(e) => onQueryChange(e)}
                    onKeyDown={(e) => onQueryKeyDown(e)}
                    placeholder="Search company name or ticker (TCS, Reliance)"
                    className="flex-1 px-3 py-2 rounded-lg border focus:ring-2 focus:ring-indigo-200 outline-none"
                    onFocus={() => { if (suggestions.length) setSuggestionsOpen(true); else scheduleSuggestions(query); }}
                    aria-autocomplete="list"
                    aria-expanded={suggestionsOpen}
                  />
                  <button onClick={() => loadCompany(query)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg flex items-center gap-2">
                    <FiSearch /> Search
                  </button>
                </div>

                {/* suggestions dropdown */}
                {suggestionsOpen && (
                  <div className="absolute left-0 right-0 bg-white border rounded mt-2 z-50 shadow max-h-60 overflow-auto">
                    {loadingSuggestions && <div className="p-2 text-sm text-slate-500">Searching…</div>}
                    {!loadingSuggestions && suggestions.length === 0 && <div className="p-2 text-sm text-slate-400">No suggestions</div>}
                    {!loadingSuggestions && suggestions.map((s, idx) => (
                      <div
                        key={`${s.label}-${idx}`}
                        onMouseDown={() => onSuggestionClick(s)}
                        onMouseEnter={() => setActiveSuggestionIndex(idx)}
                        className={`p-2 cursor-pointer flex items-center justify-between ${idx === activeSuggestionIndex ? "bg-slate-100" : ""}`}
                      >
                        <div>
                          <div className="font-medium text-sm">{s.label}</div>
                          <div className="text-xs text-slate-400">{s.ticker || s.source}</div>
                        </div>
                        <div className="text-xs text-slate-500">{s.source === "recent" ? "Recent" : s.source === "snapshot" ? "Snapshot" : ""}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3 w-full md:w-96">
                <Stat label="Top Gainers" value={topGainers.length || 0} />
                <Stat label="Top Losers" value={topLosers.length || 0} />
                <Stat label="NSE Active" value={nseActive.length || 0} />
              </div>
            </div>

            <div className="mt-4 border-t pt-4">
              {loadingCompany ? (
                <Loading text="Loading company..." />
              ) : company ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-lg font-semibold">{company.companyName || company.tickerId || query}</div>
                        <div className="text-xs text-slate-500">{company.industry || "—"}</div>
                      </div>

                      <div className="text-right">
                        <div className="text-xs text-slate-500">Price (NSE / BSE)</div>
                        <div className="text-xl font-semibold">{company.currentPrice ? `${company.currentPrice.NSE ?? company.currentPrice?.nse ?? "—"} / ${company.currentPrice.BSE ?? company.currentPrice?.bse ?? "—"}` : "—"}</div>
                        <div className={`text-sm ${Number(company.percentChange) >= 0 ? "text-green-600" : "text-red-600"}`}>{fmtPct(company.percentChange)}</div>
                        <div className="text-xs text-slate-400 mt-1">Prev close: {fmtNumber(company.stockDetailsReusableData?.prevClose ?? company.stockDetailsReusableData?.previous_close ?? company.stockDetailsReusableData?.prev_close ?? "—")}</div>
                      </div>
                    </div>

                    <div className="mt-3 p-3 rounded bg-slate-50 text-sm text-slate-600 max-h-28 overflow-auto">
                      <div className="font-medium mb-1">Company profile</div>
                      <div>{company.companyProfile?.companyDescription || company.companyProfile?.description || clamp(JSON.stringify(company.companyProfile || {}, null, 2), 800) || "Not available"}</div>
                      <div className="mt-2 text-xs">
                        <button onClick={() => { setModalTitle("Company JSON"); setModalData(company); setModalOpen(true); }} className="text-indigo-600 text-xs">View JSON</button>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-3 gap-3">
                      <Stat label="52wk High" value={fmtNumber(company.yearHigh)} />
                      <Stat label="52wk Low" value={fmtNumber(company.yearLow)} />
                      <Stat label="Market Cap" value={fmtNumber(company.stockDetailsReusableData?.marketCap || company.marketCap || "—")} />
                    </div>

                    <div className="mt-3 grid grid-cols-4 gap-3 text-sm">
                      <div className="p-2 bg-slate-50 rounded">
                        <div className="text-xs text-slate-500">P/E</div>
                        <div className="font-semibold">{fmtNumber(company.stockDetailsReusableData?.peRatio ?? company.stockDetailsReusableData?.pe ?? company.stockDetailsReusableData?.PE ?? "—")}</div>
                      </div>
                      <div className="p-2 bg-slate-50 rounded">
                        <div className="text-xs text-slate-500">EPS</div>
                        <div className="font-semibold">{fmtNumber(company.stockDetailsReusableData?.eps ?? company.stockDetailsReusableData?.EPS ?? "—")}</div>
                      </div>
                      <div className="p-2 bg-slate-50 rounded">
                        <div className="text-xs text-slate-500">Div Yield</div>
                        <div className="font-semibold">{fmtNumber(company.stockDetailsReusableData?.dividendYield ?? company.stockDetailsReusableData?.dividend_yield ?? company.stockDetailsReusableData?.div_yield ?? "—")}</div>
                      </div>
                      <div className="p-2 bg-slate-50 rounded">
                        <div className="text-xs text-slate-500">Volume</div>
                        <div className="font-semibold">{fmtNumber(company.stockDetailsReusableData?.volume ?? "—")}</div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <Card className="p-3">
                      <div className="text-xs text-slate-500">Analyst Recommendation</div>
                      <div className="text-lg font-semibold mt-2">
                        {priceTargetSummary?.mean != null ? `Analyst score: ${Number(priceTargetSummary.mean).toFixed(2)}` : "No data"}
                      </div>
                      <div className="text-xs mt-2 text-slate-400">Estimates: {priceTargetSummary?.count ?? "—"}</div>
                      <div style={{ height: 120 }}>
                        {priceTargetSummary?.mean != null ? (
                          <ResponsiveContainer width="100%" height={120}>
                            <RadialBarChart innerRadius="70%" outerRadius="100%" data={[{ name: "rec", uv: Math.max(0, Math.min(100, (5 - Number(priceTargetSummary.mean)) * 20)) }]} startAngle={180} endAngle={-0}>
                              <RadialBar minAngle={15} cornerRadius={10} dataKey="uv" />
                            </RadialBarChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="text-xs text-slate-400">No gauge data</div>
                        )}
                      </div>
                    </Card>

                    <Card className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="text-xs text-slate-500">Forecast / Price Target</div>
                        <div className="text-xs text-indigo-600 cursor-pointer" onClick={() => setShowRecSnapshots((s) => !s)}>{showRecSnapshots ? "Hide" : "Show"}</div>
                      </div>

                      <div className="mt-3">
                        {priceTargetSummary ? (
                          <>
                            <div className="text-sm text-slate-500">Mean target</div>
                            <div className="text-2xl font-semibold">{fmtNumber(priceTargetSummary.mean)}</div>
                            <div className="text-xs text-slate-400 mt-1">Median: {fmtNumber(priceTargetSummary.median)} · Estimates: {priceTargetSummary.count ?? "—"}</div>

                            {priceTargetSummary.recentSnapshot ? (
                              <div className="mt-3 text-sm">
                                <div className="text-xs text-slate-500">Recent snapshot</div>
                                <div className="font-medium">{fmtNumber(priceTargetSummary.recentSnapshot.mean)}</div>
                                <div className="text-xs text-slate-400">{priceTargetSummary.recentSnapshot.age}</div>
                              </div>
                            ) : null}
                          </>
                        ) : (
                          <div className="text-sm text-slate-400">No price target data</div>
                        )}
                        <div className="mt-2">
                          <button onClick={() => { setModalTitle("Price Target JSON"); setModalData(priceTarget); setModalOpen(true); }} className="text-xs text-indigo-600">View full price target JSON</button>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-500">Enter company to fetch details.</div>
              )}
            </div>
          </Card>

          {/* ---------------- NEW: Improved Technical / Financials / Futures UI ---------------- */}

          {company && (
            <>
              <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Technical data */}
                <InfoSection
                  title="Technical Data"
                  rightAction={
                    <div className="flex items-center gap-2">
                      <button
                        className="text-xs text-indigo-600 flex items-center gap-1"
                        onClick={() => { setModalTitle("Technical JSON"); setModalData(company.stockTechnicalData); setModalOpen(true); }}
                      >
                        <FiClipboard /> View JSON
                      </button>
                    </div>
                  }
                  badge="Charts and indicators"
                >
                  {/* summary tiles from technical data if present */}
                  <div className="grid grid-cols-2 gap-2">
                    {company.stockTechnicalData && company.stockTechnicalData.samplePrices ? (
                      (company.stockTechnicalData.samplePrices || []).slice(0, 4).map((s, i) => (
                        <div key={i} className="p-2 bg-slate-50 rounded text-sm">
                          <div className="text-xs text-slate-500">{s.label ?? `T+${i}`}</div>
                          <div className="font-medium">{fmtNumber(s.price ?? s.value)}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-400">No quick price tiles available</div>
                    )}
                  </div>

                  {/* compact charts: RSI and MACD */}
                  <div>
                    {(() => {
                      const rsiSeries = buildSeriesFromTechnical(company.stockTechnicalData, "rsi");
                      if (rsiSeries.length) {
                        return (
                          <div className="mb-3" style={{ height: 140 }}>
                            <div className="text-xs text-slate-500 mb-1">RSI</div>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={rsiSeries}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" hide />
                                <YAxis domain={[0, 100]} tickFormatter={(v) => v} />
                                <Tooltip formatter={(v) => Number(v).toFixed(2)} />
                                <Line type="monotone" dataKey="value" stroke="#1f6feb" dot={false} strokeWidth={2} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      }
                      return null;
                    })()}

                    {(() => {
                      const macdSeries = buildSeriesFromTechnical(company.stockTechnicalData, "macd");
                      if (macdSeries.length) {
                        return (
                          <div className="mb-3" style={{ height: 140 }}>
                            <div className="text-xs text-slate-500 mb-1">MACD</div>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={macdSeries}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" hide />
                                <YAxis tickFormatter={(v) => v} />
                                <Tooltip formatter={(v) => Number(v).toFixed(2)} />
                                <Line type="monotone" dataKey="value" stroke="#ef4444" dot={false} strokeWidth={2} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      }
                      return null;
                    })()}
                  </div>

                  {/* cleaned technical key/value rows */}
                  <div className="space-y-2">
                    {company.stockTechnicalData ? (
                      Object.entries(company.stockTechnicalData).slice(0, 12).map(([k, v]) => (
                        <KVRow key={k} label={k} value={v} />
                      ))
                    ) : (
                      <div className="text-sm text-slate-400">No technical data available</div>
                    )}
                  </div>

                  {/* any long arrays shown with collapsible lists */}
                  <div>
                    <CollapsibleList label="Large arrays / indicators" items={Object.values(company.stockTechnicalData || {})} previewItems={2} />
                  </div>
                </InfoSection>

                {/* Financials & Key Metrics */}
                <InfoSection
                  title="Financials & Key Metrics"
                  rightAction={
                    <div className="flex items-center gap-2">
                      <button className="text-xs text-indigo-600" onClick={() => { setModalTitle("Financials JSON"); setModalData(company.financials); setModalOpen(true); }}>View JSON</button>
                    </div>
                  }
                  badge="Key metrics, financial statements"
                >
                  {/* Key metrics grid */}
                  <div>
                    <div className="text-xs text-slate-500 mb-2">Key metrics (sample)</div>
                    {company.keyMetrics ? (
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(company.keyMetrics).slice(0, 8).map(([k, v]) => (
                          <div key={k} className="p-2 bg-slate-50 rounded text-sm">
                            <div className="text-xs text-slate-500 mb-1">{k}</div>
                            <div>{renderValueReadable(v)}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-slate-400">No key metrics</div>
                    )}
                  </div>

                  {/* Financial summary: try to render a table if quarters/periods exist */}
                  <div>
                    <div className="text-xs text-slate-500 mb-2">Financial summary</div>
                    {company.financials ? (
                      <>
                        {Array.isArray(company.financials.quarters || company.financials.periods || company.financials.rows) ? (
                          (() => {
                            const rows = company.financials.quarters || company.financials.periods || company.financials.rows;
                            const cols = Array.from(rows.slice(0, 6).reduce((s, r) => { Object.keys(r || {}).forEach((k) => s.add(k)); return s; }, new Set()));
                            return (
                              <div className="overflow-auto max-h-48">
                                <table className="w-full text-xs">
                                  <thead className="text-left text-gray-500 sticky top-0 bg-white">
                                    <tr>
                                      {cols.map((c) => <th key={c} className="pr-4">{c}</th>)}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {rows.slice(0, 8).map((r, idx) => (
                                      <tr key={idx} className="border-t">
                                        {cols.map((c) => {
                                          const rawVal = r[c] ?? r[c.toLowerCase()] ?? r[c.toUpperCase()] ?? (typeof r[c] === "string" ? r[c] : null);
                                          return <td key={c} className="py-1 pr-4">{renderValueReadable(rawVal)}</td>;
                                        })}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            );
                          })()
                        ) : company.financials.stockFinancialMap && typeof company.financials.stockFinancialMap === "object" ? (
                          <div className="space-y-2 max-h-48 overflow-auto">
                            {Object.entries(company.financials.stockFinancialMap).slice(0, 6).map(([section, items]) => (
                              <div key={section}>
                                <div className="text-xs text-slate-500 mb-1">{section}</div>
                                {Array.isArray(items) ? (
                                  <div className="text-sm space-y-1">
                                    {items.slice(0, 4).map((it, i) => (
                                      <div key={i} className="flex justify-between text-xs">
                                        <div className="text-slate-600">{it.displayName || it.key || Object.keys(it)[0]}</div>
                                        <div className="font-medium">{renderValueReadable(it.value ?? it.val ?? it.amount ?? it[Object.keys(it)[1]] ?? it)}</div>
                                      </div>
                                    ))}
                                    {items.length > 4 && <div className="text-xs text-slate-400">+{items.length - 4} more</div>}
                                  </div>
                                ) : (
                                  <div className="text-sm">{clamp(JSON.stringify(items), 200)}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm text-slate-600">{clamp(JSON.stringify(company.financials || {}).slice(0, 800))}</div>
                        )}
                      </>
                    ) : (
                      <div className="text-sm text-slate-400">No financials available</div>
                    )}
                  </div>

                  {/* quick actions */}
                  <div className="flex gap-2">
                    <button className="px-3 py-1 bg-slate-50 border rounded text-xs" onClick={() => { setModalTitle("Financials JSON"); setModalData(company.financials); setModalOpen(true); }}>Open JSON</button>
                    <button className="px-3 py-1 bg-slate-50 border rounded text-xs" onClick={() => { copyToClipboard(clamp(JSON.stringify(company.financials || {}, null, 2), 10000)); }}>Copy summary</button>
                  </div>
                </InfoSection>

                {/* Futures & Corporate */}
                <InfoSection
                  title="Futures & Corporate"
                  rightAction={
                    <div className="text-xs text-indigo-600">
                      <button onClick={() => { setModalTitle("Futures & Corporate JSON"); setModalData({ futureExpiryDates: company.futureExpiryDates, shareholding: company.shareholding, corporate: company.stockCorporateActionData }); setModalOpen(true); }}>View JSON</button>
                    </div>
                  }
                  badge="Expiry dates, shareholding, corporate actions"
                >
                  <div>
                    <div className="text-xs text-slate-500">Future expiry dates</div>
                    {Array.isArray(company.futureExpiryDates) && company.futureExpiryDates.length ? (
                      <ul className="list-disc ml-5 text-sm">
                        {company.futureExpiryDates.slice(0, 6).map((d, i) => <li key={i}>{String(d)}</li>)}
                      </ul>
                    ) : <div className="text-sm text-slate-400">No future expiry dates</div>}
                  </div>

                  <div>
                    <div className="text-xs text-slate-500">Shareholding (top)</div>
                    {company.shareholding ? (
                      Array.isArray(company.shareholding) ? (
                        <div className="space-y-1">
                          {company.shareholding.slice(0, 6).map((s, i) => {
                            // attempt to extract structure like { displayName, categories: [{holdingDate, percentage}, ...] }
                            const title =
                              s.categoryName || s.displayName || s.holderName || (typeof s === "object" && (s.name || s.label)) || `Holder ${i+1}`;
                            const cats = s.categories || s.holdings || s.data || (Array.isArray(s) ? s : []);
                            const pct = (Array.isArray(cats) && cats.length && (cats[0].percentage ?? cats[0].percent)) ? `${cats[0].percentage ?? cats[0].percent}%` : null;
                            return (
                              <div key={i} className="p-2 bg-slate-50 rounded text-sm flex items-center justify-between">
                                <div>
                                  <div className="font-medium">{title}</div>
                                  <div className="text-xs text-slate-500">{cats && cats[0] && (cats[0].holdingDate || cats[0].date) ? cats[0].holdingDate || cats[0].date : ""}</div>
                                </div>
                                <div className="text-sm font-semibold text-slate-800">{pct ?? "—"}</div>
                              </div>
                            );
                          })}
                          {company.shareholding.length > 6 && <div className="text-xs text-slate-400">+{company.shareholding.length - 6} more</div>}
                        </div>
                      ) : (
                        <div className="text-sm">{clamp(JSON.stringify(company.shareholding), 400)}</div>
                      )
                    ) : <div className="text-sm text-slate-400">No shareholding data</div>}
                  </div>

                  <div>
                    <div className="text-xs text-slate-500">Corporate actions</div>
                    {company.stockCorporateActionData ? (
                      Array.isArray(company.stockCorporateActionData.actions || company.stockCorporateActionData.dividend || company.stockCorporateActionData) ? (
                        <div className="space-y-1">
                          {(company.stockCorporateActionData.dividend || company.stockCorporateActionData.actions || company.stockCorporateActionData).slice(0, 6).map((a, i) => (
                            <div key={i} className="p-2 bg-slate-50 rounded text-sm">
                              <div className="font-medium">{a.companyName || a.tickerId || a.ticker || a.type || `Action ${i+1}`}</div>
                              <div className="text-xs text-slate-500">{a.remarks || a.recordDate || a.date || clamp(JSON.stringify(a).slice(0, 80))}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-sm">{clamp(JSON.stringify(company.stockCorporateActionData), 400)}</div>
                      )
                    ) : <div className="text-sm text-slate-400">No corporate actions</div>}
                  </div>
                </InfoSection>
              </div>

              {/* Indicators compact charts (unchanged behavior, improved layout) */}
              <div className="mt-6">
                <Card>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <div className="text-sm font-semibold">Indicator Charts</div>
                      <div className="text-xs text-slate-400">RSI / MACD (if available)</div>
                    </div>
                    <div className="text-xs text-slate-400">Overview</div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(() => {
                      const rsiSeries = buildSeriesFromTechnical(company.stockTechnicalData, "rsi");
                      if (rsiSeries.length) {
                        return (
                          <div key="rsi" style={{ height: 160 }}>
                            <div className="text-xs text-slate-500 mb-1">RSI</div>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={rsiSeries}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" hide />
                                <YAxis domain={[0, 100]} />
                                <Tooltip formatter={(v) => Number(v).toFixed(2)} />
                                <Line type="monotone" dataKey="value" stroke="#1f6feb" dot={false} strokeWidth={2} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      }
                      return null;
                    })()}

                    {(() => {
                      const macdSeries = buildSeriesFromTechnical(company.stockTechnicalData, "macd");
                      if (macdSeries.length) {
                        return (
                          <div key="macd" style={{ height: 160 }}>
                            <div className="text-xs text-slate-500 mb-1">MACD</div>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={macdSeries}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" hide />
                                <YAxis />
                                <Tooltip formatter={(v) => Number(v).toFixed(2)} />
                                <Line type="monotone" dataKey="value" stroke="#ef4444" dot={false} strokeWidth={2} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      }
                      return null;
                    })()}
                  </div>
                </Card>
              </div>
            </>
          )}
        </div>

        {/* right column (kept largely unchanged) */}
        <div className="lg:col-span-4 space-y-4">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">Market Movers — NSE Active</div>
                <div className="text-xs text-slate-400">Live snapshot</div>
              </div>
              <div className="text-xs text-slate-400">{snapshotLoading ? "Refreshing…" : "Snapshot"}</div>
            </div>

            <div className="mt-3 space-y-2">
              {nseActive && nseActive.length ? (
                nseActive.slice(0, 6).map((r) => (
                  <div key={r.ticker || r.company} className="flex items-center justify-between text-sm">
                    <div className="flex-1">
                      <div className="font-medium">{r.company}</div>
                      <div className="text-xs text-slate-400">{r.ticker}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{fmtNumber(r.price)}</div>
                      <div className={`text-xs ${Number(r.percent_change || r.percentChange) >= 0 ? "text-green-600" : "text-red-600"}`}>{fmtPct(r.percent_change ?? r.percentChange)}</div>
                    </div>
                  </div>
                ))
              ) : topGainers && topGainers.length ? (
                topGainers.map((g) => (
                  <div key={g.ticker_id || g.ticker} className="flex items-center justify-between text-sm">
                    <div className="flex-1">
                      <div className="font-medium">{g.company_name || g.company || g.ticker}</div>
                      <div className="text-xs text-slate-400">{g.ticker_id || g.ticker}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{fmtNumber(g.price)}</div>
                      <div className={`text-xs ${Number(g.percent_change || g.percentChange) >= 0 ? "text-green-600" : "text-red-600"}`}>{fmtPct(g.percent_change ?? g.percentChange)}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-400">No data</div>
              )}
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">52-week Highs / Lows (sample)</div>
                <div className="text-xs text-slate-400">From API</div>
              </div>
              <div className="text-xs text-slate-400">Snapshot</div>
            </div>

            <div className="mt-3 text-sm">
              {week52 ? (
                <>
                  <div className="mb-2 text-xs text-slate-500">NSE - Highs</div>
                  {(week52.NSE_52WeekHighLow?.high52Week || []).slice(0, 4).map((h) => (
                    <div key={h.ticker} className="flex justify-between"><div>{h.company}</div><div className="font-medium">{fmtNumber(h.price)}</div></div>
                  ))}
                </>
              ) : <div className="text-slate-400">No 52-week data</div>}
            </div>
          </Card>

          {/* Recent news card (if present) */}
          <Card>
            <div className="flex items-center justify-between">
              <div><div className="text-sm font-semibold">Recent News</div><div className="text-xs text-slate-400">From stock.recentNews</div></div>
              <div className="text-xs text-indigo-600 cursor-pointer" onClick={() => { setModalTitle("Recent News JSON"); setModalData(company?.recentNews); setModalOpen(true); }}>View JSON</div>
            </div>

            <div className="mt-2">
              {company && Array.isArray(company.recentNews) && company.recentNews.length ? (
                company.recentNews.slice(0, 6).map((n, i) => (
                  <div key={i} className="mb-3">
                    <div className="font-medium text-sm">
                      {n.url || n.link ? (
                        <a href={n.url || n.link} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">
                          {n.title || n.headline || n.name || clamp(String(n).slice(0, 80))}
                        </a>
                      ) : (
                        <span>{n.title || n.headline || n.name || clamp(String(n).slice(0, 80))}</span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500">{n.source || n.publisher || n.date || n.publishedAt || ""}</div>
                  </div>
                ))
              ) : <div className="text-sm text-slate-400">No recent news</div>}
            </div>
          </Card>
        </div>
      </div>

      {/* the rest of the dashboard remains unchanged (historical charts, top movers, analyst targets, mutual funds, sector heatmap, etc.) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <Card className="flex flex-col h-96">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm font-semibold">Historical Price — 1 Year</div>
                <div className="text-xs text-slate-400">Endpoint: /api/historical_data (preferred via research when available)</div>
              </div>

              <div className="flex items-center gap-2">
                <button onClick={() => {
                  const rows = priceSetForChart.map((p) => ({ date: p.date, price: p.value }));
                  exportTableToCSV(rows, `${(company?.tickerId || query).toLowerCase()}-historical.csv`);
                }} className="text-xs px-3 py-1 bg-slate-50 border rounded">Export CSV</button>
                <button onClick={() => exportReportPdf()} className="text-xs px-3 py-1 bg-slate-50 border rounded"><FiDownload/> PDF</button>
              </div>
            </div>

            <div className="flex-1">
              {priceSetForChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={priceSetForChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e6e6e6" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={(v) => fmtNumber(v)} />
                    <Tooltip formatter={(v) => fmtNumber(v)} />
                    <Line type="monotone" dataKey="value" stroke="#4f46e5" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">No historical price — search a symbol to load historical data (Perplexity preferred).</div>
              )}
            </div>
          </Card>
        </div>

        <div>
          <Card>
            <div className="text-sm font-semibold mb-3">Snapshot — Top Movers</div>
            <div className="text-xs text-slate-400 mb-2">Real-time</div>

            <div className="mt-2">
              <div className="text-xs text-slate-500">Top Gainers</div>
              {topGainers.length ? topGainers.slice(0, 5).map((g) => (
                <div key={g.ticker_id || g.ticker} className="flex justify-between items-center text-sm">
                  <div>{g.company_name || g.company || g.ticker}</div>
                  <div className="text-right"><div className="font-medium">{fmtNumber(g.price)}</div><div className="text-xs text-green-600">{fmtPct(g.percent_change ?? g.percentChange)}</div></div>
                </div>
              )) : <div className="text-sm text-slate-400">No data</div>}

              <div className="mt-4 text-xs text-slate-500">Top Losers</div>
              {topLosers.length ? topLosers.slice(0, 5).map((g) => (
                <div key={g.ticker_id || g.ticker} className="flex justify-between items-center text-sm">
                  <div>{g.company_name || g.company || g.ticker}</div>
                  <div className="text-right"><div className="font-medium">{fmtNumber(g.price)}</div><div className="text-xs text-red-600">{fmtPct(g.percent_change ?? g.percentChange)}</div></div>
                </div>
              )) : <div className="text-sm text-slate-400">No data</div>}
            </div>
          </Card>
        </div>
      </div>

      {/* bottom: Analysts, mutual funds, commodities (unchanged) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <Card>
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">Analyst Targets & Forecasts</div>
              <div className="text-xs text-slate-400">stock_target_price / stock_forecasts</div>
            </div>

            {priceTarget ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-3 bg-slate-50 rounded"><div className="text-xs text-slate-500">Mean Target</div><div className="font-semibold">{fmtNumber(priceTarget.priceTarget?.Mean ?? priceTarget.priceTarget?.UnverifiedMean ?? priceTarget?.Mean ?? priceTarget?.mean)}</div></div>
                  <div className="p-3 bg-slate-50 rounded"><div className="text-xs text-slate-500">Median</div><div className="font-semibold">{fmtNumber(priceTarget.priceTarget?.Median ?? priceTarget?.Median ?? priceTarget?.median)}</div></div>
                  <div className="p-3 bg-slate-50 rounded"><div className="text-xs text-slate-500">Number Estimates</div><div className="font-semibold">{fmtNumber(priceTarget.priceTarget?.NumberOfEstimates ?? priceTarget.priceTarget?.NumberOfRecommendations ?? priceTarget?.NumberOfEstimates ?? priceTarget?.count)}</div></div>
                </div>

                <div className="mt-4">
                  <div className="text-xs text-slate-500">Recommendation snapshot</div>
                  {priceTarget.priceTargetSnapshots?.PriceTargetSnapshot?.length ? (
                    <table className="w-full text-xs mt-2">
                      <thead className="text-left text-gray-500"><tr><th>Age</th><th>Mean</th><th># Estimates</th></tr></thead>
                      <tbody>
                        {priceTarget.priceTargetSnapshots.PriceTargetSnapshot.map((s, idx) => (
                          <tr key={idx} className="border-t"><td>{s.Age || s.age}</td><td>{fmtNumber(s.Mean ?? s.UnverifiedMean)}</td><td>{s.NumberOfEstimates ?? "-"}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  ) : <div className="text-sm text-slate-400 mt-2">No snapshots</div>}
                </div>
              </>
            ) : <div className="text-sm text-slate-400">No analyst targets for this symbol.</div>}
          </Card>
        </div>

        <div>
          <Card>
            <div className="text-sm font-semibold mb-3">Mutual Funds & Commodities</div>

            <div>
              <div className="text-xs text-slate-500 mb-2">Mutual Funds (Large Cap sample)</div>
              {mutualFunds?.Equity?.["Large Cap"] ? mutualFunds.Equity["Large Cap"].slice(0, 6).map((f, i) => (
                <div key={i} className="flex justify-between text-sm mb-2"><div>{f.schemeName || f.fund_name}</div><div className="font-medium">{fmtNumber(f.latest_nav)}</div></div>
              )) : <div className="text-sm text-slate-400">No mutual funds snapshot</div>}
            </div>

            <div className="mt-4">
              <div className="text-xs text-slate-500 mb-2">Price Shockers</div>
              {priceShockers.length ? priceShockers.slice(0, 6).map((s) => (<div key={s.ticker} className="flex justify-between text-sm mb-2"><div>{s.company || s.ticker}</div><div className="font-medium">{fmtNumber(s.price)}</div></div>)) : <div className="text-sm text-slate-400">No shockers</div>}
            </div>

            <div className="mt-4">
              <div className="text-xs text-slate-500 mb-2">Commodities</div>
              {normalizedCommodities.length ? normalizedCommodities.slice(0, 6).map((c) => (<div key={c.id || c.name} className="flex justify-between text-sm mb-2"><div>{c.name || "—"}</div><div className="font-medium">{fmtNumber(c.lastTradedPrice ?? "—")}</div></div>)) : <div className="text-sm text-slate-400">No commodities</div>}
            </div>
          </Card>
        </div>
      </div>

      {/* industry & mf search (unchanged) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <Card>
          <div className="flex items-center justify-between mb-3"><div className="text-sm font-semibold">Industry Search</div><div className="text-xs text-slate-400">industry_search</div></div>
          <div className="flex gap-2">
            <input value={industryQuery} onChange={(e) => setIndustryQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doIndustrySearch(industryQuery)} className="flex-1 px-3 py-2 rounded-lg border" placeholder="Search industry (e.g. Technology)" />
            <button onClick={() => doIndustrySearch(industryQuery)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg">Search</button>
          </div>

          <div className="mt-3">
            {industryResults.length ? industryResults.slice(0, 8).map((it) => (
              <div key={it.id} className="flex justify-between items-start p-2 border-b last:border-b-0">
                <div><div className="font-medium">{it.commonName}</div><div className="text-xs text-slate-500">{it.mgIndustry} • {it.mgSector}</div></div>
                <div className="text-right text-xs"><div>{it.exchangeCodeNsi || it.exchangeCodeNse || "-"}</div><div className="text-xs text-slate-400">{it.activeStockTrends?.overallRating}</div></div>
              </div>
            )) : <div className="text-sm text-slate-400">No industry results</div>}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3"><div className="text-sm font-semibold">Mutual Fund Search</div><div className="text-xs text-slate-400">mutual_fund_search</div></div>
          <div className="flex gap-2">
            <input value={mfQuery} onChange={(e) => setMfQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doMfSearch(mfQuery)} className="flex-1 px-3 py-2 rounded-lg border" placeholder="Search mutual funds by name or ISIN" />
            <button onClick={() => doMfSearch(mfQuery)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg">Search</button>
          </div>

          <div className="mt-3">
            {mfResults.length ? mfResults.slice(0, 8).map((m) => (
              <div key={m.id} className="flex justify-between items-start p-2 border-b last:border-b-0">
                <div><div className="font-medium">{m.schemeName || m.scheme_name}</div><div className="text-xs text-slate-500">{m.isin}</div></div>
                <div className="text-sm text-slate-600">{m.schemeType || m.scheme_type}</div>
              </div>
            )) : <div className="text-sm text-slate-400">No mutual fund results</div>}
          </div>
        </Card>
      </div>

      {/* sector heatmap — unchanged but clearer labels */}
      <div className="mt-6">
        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold">Sector Heatmap</div>
            <div className="text-xs text-slate-400">Avg % move + counts (industry + movers)</div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {sectorTiles.length ? sectorTiles.slice(0, 12).map((s) => {
              const score = Math.max(-20, Math.min(20, Number(s.avgPct) || 0));
              const pct = Math.round(score * 100) / 100;
              const hue = Math.round((score + 20) * (120 / 40));
              const bg = `hsl(${hue}, 70%, 92%)`;
              const text = `hsl(${hue}, 70%, 20%)`;
              return (
                <div key={s.sector} className="p-3 rounded" style={{ background: bg, color: text }}>
                  <div className="text-sm font-semibold">{s.sector}</div>
                  <div className="text-xs mt-1">Count: {s.count}</div>
                  <div className="text-xs">Avg move: {fmtNumber(s.avgPct)}%</div>
                </div>
              );
            }) : <div className="text-sm text-slate-400">No sector data</div>}
          </div>
        </Card>
      </div>

      {error && (
        <div className="fixed right-6 bottom-6 bg-red-600 text-white p-3 rounded-lg shadow z-50">
          <div className="text-sm font-semibold">Error</div>
          <div className="text-xs mt-1 max-w-xs">{String(error)}</div>
          <div className="text-xs mt-2 opacity-80">Server errors: {serverErrorCount}</div>
        </div>
      )}
    </div>
  );
}

/* ------------------ helpers ------------------ */
function recommendationLabel(mean) {
  if (mean == null) return "—";
  const m = Number(mean);
  if (Number.isNaN(m)) return String(mean);
  const r = Math.round(m);
  switch (r) {
    case 1: return "Buy";
    case 2: return "Outperform";
    case 3: return "Hold";
    case 4: return "Underperform";
    case 5: return "Sell";
    default:
      if (m < 2) return "Buy";
      if (m < 3) return "Outperform";
      if (m < 4) return "Hold";
      return "Sell";
  }
}
