// src/components/DealTracker.jsx
import React, { useEffect, useState, useRef } from "react";
import { RefreshCcw, ExternalLink, Eye, Search, Clock } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || window?.API_URL || "";

/* ---------- helpers ---------- */
function getDomain(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace(/^www\./, "");
  } catch (e) {
    return null;
  }
}
function getFavicon(url) {
  const domain = getDomain(url);
  if (!domain) return null;
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
}
const clampStyle = {
  display: "-webkit-box",
  WebkitLineClamp: 3,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

function parseValueFromString(raw) {
  if (!raw && raw !== 0) return null;
  if (typeof raw === "number") return raw;
  const s = String(raw).toLowerCase().replace(/,/g, "").trim();
  const m = s.match(/([\d.]+)\s*(billion|million|k|thousand|m|bn|mm)?/i);
  if (!m) return null;
  let num = parseFloat(m[1]);
  const unit = (m[2] || "").toLowerCase();
  if (unit.includes("b") || unit === "bn" || unit === "billion") num *= 1_000_000_000;
  else if (unit.includes("m") || unit === "million" || unit === "mm") num *= 1_000_000;
  else if (unit === "k" || unit === "thousand") num *= 1_000;
  return Math.round(num);
}
function formatMoney(n) {
  if (n == null) return "Undisclosed";
  try {
    if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B USD`;
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M USD`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k USD`;
    return `${n} USD`;
  } catch {
    return String(n);
  }
}

/* ---------- component ---------- */
export default function DealTracker() {
  // default to News per your request
  const [tab, setTab] = useState("news"); // 'deals' | 'news'
  const [region, setRegion] = useState("india");
  const [deals, setDeals] = useState([]);
  const [news, setNews] = useState([]);
  const [loadingDeals, setLoadingDeals] = useState(false);
  const [loadingNews, setLoadingNews] = useState(false);
  const [error, setError] = useState(null);
  const [debugItem, setDebugItem] = useState(null);
  const [sectorFilter, setSectorFilter] = useState("all");
  const [sortBy, setSortBy] = useState("date");
  const [limit, setLimit] = useState(9);
  const [newsQuery, setNewsQuery] = useState("");
  const mounted = useRef(false);

  /* Normalize deal item (incoming shapes vary) */
  const normalizeDeal = (it, idx) => {
    const sourceUrl = it.source ?? it.url ?? it.link ?? it.source_url ?? null;
    let imageUrl = it.image || it.logo || it.og_image || it.ogImage || null;
    if (!imageUrl && sourceUrl) imageUrl = getFavicon(sourceUrl);
    const rawValue = it.value ?? it.amount ?? it.deal_value ?? it.size ?? it.value_text ?? null;
    const numeric = parseValueFromString(rawValue);
    const displayValue = numeric ? formatMoney(numeric) : (rawValue || "Undisclosed");
    const parsedDate = it.date ? new Date(it.date) : (it.timestamp ? new Date(it.timestamp) : null);
    const summary = it.summary || it.one_liner || it.oneLiner || it.description || it.snippet || null;

    return {
      id: it.id ?? `${it.acquirer ?? "A"}-${it.target ?? "T"}-${idx}`,
      acquirer: it.acquirer ?? it.buyer ?? it.investor ?? "Unknown",
      target: it.target ?? it.company ?? it.asset ?? "Unknown",
      valueRaw: rawValue,
      value: displayValue,
      valueNumber: numeric,
      sector: it.sector ?? it.industry ?? "N/A",
      type: it.type ?? "M&A",
      region: it.region ?? region,
      date: parsedDate,
      source: sourceUrl,
      image: imageUrl,
      summary,
      raw: it,
    };
  };

  /* Normalize news item (IndianAPI /news) */
  const normalizeNews = (it, idx) => {
    const sourceUrl = it.url ?? it.link ?? it.source_url ?? null;
    const domain = getDomain(sourceUrl) || it.source || "source";
    const imageUrl = it.image || it.urlToImage || it.thumbnail || getFavicon(sourceUrl);
    const title = it.title ?? it.headline ?? it.heading ?? "Untitled";
    const snippet = it.description ?? it.summary ?? it.snippet ?? "";
    const date = it.publishedAt ? new Date(it.publishedAt) : (it.date ? new Date(it.date) : null);
    return {
      id: it.id ?? `${domain}-${idx}`,
      title,
      snippet,
      source: domain,
      sourceUrl,
      image: imageUrl,
      date,
      raw: it,
    };
  };

  /* Fetch deals from your backend proxy */
  const fetchDeals = async (opts = {}) => {
    const L = opts.limit || limit || 12;
    try {
      setLoadingDeals(true);
      setError(null);
      const url = `${API_BASE}/api/perplexity/deals?region=${encodeURIComponent(region)}&limit=${L}`;
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Upstream error ${res.status}: ${txt || res.statusText}`);
      }
      const json = await res.json();
      let arr = Array.isArray(json) ? json : (json.parsed ?? json.deals ?? json.data ?? json.items ?? []);
      if (!Array.isArray(arr) && json && typeof json === "object") {
        const candidates = [json.parsed, json.result, json.data, json.items];
        for (const c of candidates) if (Array.isArray(c)) arr = c;
      }
      if (!Array.isArray(arr)) {
        console.warn("DealTracker: unexpected deals payload", json);
        setDeals([]);
        setError("Unexpected response from deals API (see console).");
        return;
      }
      const norm = arr.map((it, i) => normalizeDeal(it, i));
      setDeals(norm);
    } catch (err) {
      console.error("DealTracker fetchDeals error:", err);
      setError("Failed to load deals. See console for details.");
      setDeals([]);
    } finally {
      setLoadingDeals(false);
    }
  };

  /* Fetch news from IndianAPI via your backend proxy (GET) */
  const fetchNews = async (opts = {}) => {
    try {
      setLoadingNews(true);
      setError(null);
      const url = `${API_BASE}/api/news`;
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Upstream error ${res.status}: ${txt || res.statusText}`);
      }
      const json = await res.json();
      let arr = Array.isArray(json) ? json : (json.data ?? json.articles ?? []);
      if (!Array.isArray(arr) && json && typeof json === "object") {
        const candidates = [json.data, json.articles, json.items];
        for (const c of candidates) if (Array.isArray(c)) arr = c;
      }
      if (!Array.isArray(arr)) {
        console.warn("DealTracker: unexpected news payload", json);
        setNews([]);
        setError("Unexpected response from news API (see console).");
        return;
      }
      const norm = arr.map((it, i) => normalizeNews(it, i));
      setNews(norm);
    } catch (err) {
      console.error("DealTracker fetchNews error:", err);
      setError("Failed to load news. See console for details.");
      setNews([]);
    } finally {
      setLoadingNews(false);
    }
  };

  useEffect(() => {
    mounted.current = true;
    // fetch both so UI is ready (news is default)
    fetchNews();
    fetchDeals({ limit });
    return () => { mounted.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region]);

  // derived / UI data for deals tab
  const sectors = Array.from(new Set(deals.map(d => d.sector).filter(Boolean))).slice(0, 20);
  const filteredDeals = deals.filter(d => sectorFilter === "all" ? true : d.sector === sectorFilter);
  const sortedDeals = filteredDeals.slice().sort((a, b) => {
    if (sortBy === "value") {
      const va = a.valueNumber ?? 0; const vb = b.valueNumber ?? 0; return vb - va;
    }
    const da = a.date ? a.date.getTime() : 0; const db = b.date ? b.date.getTime() : 0; return db - da;
  });

  // news filtering
  const newsFiltered = newsQuery.trim()
    ? news.filter(n => (n.title + " " + (n.snippet || "") + " " + (n.source || "")).toLowerCase().includes(newsQuery.toLowerCase()))
    : news;

  const loadMoreDeals = () => {
    const newLimit = limit + 6;
    setLimit(newLimit);
    fetchDeals({ limit: newLimit });
  };

  // Switch from News -> Deals and pre-load deals (Next: Deals)
  const goToDeals = async () => {
    setTab("deals");
    if (deals.length === 0) {
      await fetchDeals({ limit });
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <header className="mb-8">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-gray-900">Tracking the World of Deals</h1>
            <p className="mt-1 text-gray-600">
              Live updates on private equity, M&A, and buyout activity — combined from Perplexity (deals) and IndianAPI (news).
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select value={region} onChange={(e)=>{ setRegion(e.target.value); setLimit(9); }} aria-label="Select region"
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white text-sm shadow-sm">
              <option value="global">🌍 Global</option>
              <option value="india">🇮🇳 India</option>
              <option value="asia">Asia</option>
              <option value="europe">Europe</option>
              <option value="usa">United States</option>
            </select>

            <button onClick={() => { fetchDeals({ limit }); fetchNews(); }} className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800 transition" title="Refresh">
              <RefreshCcw size={16} /> Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-3 border-b pb-3 mb-4">
          <button className={`px-4 py-2 rounded-t-lg ${tab === "deals" ? "bg-white border border-b-0 shadow-sm" : "text-gray-600"}`} onClick={() => setTab("deals")}>Deals</button>
          <button className={`px-4 py-2 rounded-t-lg ${tab === "news" ? "bg-white border border-b-0 shadow-sm" : "text-gray-600"}`} onClick={() => setTab("news")}>News</button>

          {tab === "deals" && (
            <div className="ml-auto flex items-center gap-3">
              <label className="text-sm text-gray-600">Sector:</label>
              <select value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)} className="border rounded px-3 py-1 text-sm">
                <option value="all">All</option>
                {sectors.map(s => <option key={s} value={s}>{s}</option>)}
              </select>

              <label className="text-sm text-gray-600 ml-3">Sort:</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="border rounded px-3 py-1 text-sm">
                <option value="date">Newest</option>
                <option value="value">By deal value</option>
              </select>
            </div>
          )}

          {tab === "news" && (
            <div className="ml-auto flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" size={14}/>
                <input value={newsQuery} onChange={(e)=>setNewsQuery(e.target.value)} placeholder="Search news..." className="pl-8 pr-3 py-2 border rounded text-sm w-64" />
              </div>

              <button onClick={goToDeals} className="ml-2 inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">
                Next: Deals
              </button>
            </div>
          )}
        </div>
      </header>

      <section>
        {tab === "deals" ? (
          <>
            {loadingDeals ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => <div key={i} className="animate-pulse bg-white rounded-2xl p-5 border border-gray-100 min-h-[160px]" />)}
              </div>
            ) : error ? (
              <div className="text-center text-red-600 py-12">{error}</div>
            ) : sortedDeals.length === 0 ? (
              <div className="text-center text-gray-500 py-12">No deals found for <strong>{region}</strong>.</div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {sortedDeals.map((d) => (
                    <article key={d.id} className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm hover:shadow-md transition flex flex-col">
                      <div className="flex gap-3">
                        <div className="w-20 h-20 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center border flex-shrink-0">
                          {d.image ? <img src={d.image} alt={`${d.target} img`} className="object-contain w-full h-full" onError={(e)=>{ e.currentTarget.onerror=null; e.currentTarget.src=getFavicon(d.source) || 'https://via.placeholder.com/64?text=DE'; }} /> : <div className="text-sm font-medium text-gray-600">{(d.target||"NA").slice(0,2).toUpperCase()}</div>}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-start gap-3">
                            <div className="min-w-0">
                              <h3 className="text-base font-semibold text-gray-900 leading-tight">
                                <span className="block truncate">{d.acquirer}</span>
                                <small className="text-gray-400 mx-1">→</small>
                                <span className="block truncate">{d.target}</span>
                              </h3>
                              {d.summary && <p className="mt-2 text-sm text-gray-600" style={clampStyle}>{d.summary}</p>}
                            </div>

                            <div className="text-right flex-shrink-0">
                              <div className="text-xs text-gray-500"><Clock size={12} className="inline-block mr-1" />{d.date ? d.date.toLocaleDateString() : "N/A"}</div>
                              <div className="mt-2 text-lg font-bold text-gray-900">{d.value}</div>
                            </div>
                          </div>

                          <div className="mt-3 flex flex-wrap gap-2 items-center">
                            <span className="text-xs bg-gray-100 px-2 py-1 rounded-full text-gray-700">{d.sector}</span>
                            <span className="text-xs bg-blue-50 px-2 py-1 rounded-full text-blue-700">{d.type}</span>
                            <span className="text-xs px-2 py-1 rounded-full text-gray-500">{d.region}</span>
                          </div>

                          <div className="mt-4 flex items-center justify-between">
                            <div className="text-sm">
                              {d.source ? (
                                <a href={d.source} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-blue-600 hover:underline">
                                  {getDomain(d.source)} <ExternalLink size={14} />
                                </a>
                              ) : <span className="text-xs text-gray-400">Source not provided</span>}
                            </div>

                            <div className="flex items-center gap-2">
                              <button onClick={() => setDebugItem(d)} className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-50 inline-flex items-center gap-2"><Eye size={14}/> Raw</button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>

                <div className="mt-6 flex justify-center">
                  <button onClick={loadMoreDeals} className="inline-flex items-center gap-2 px-4 py-2 border rounded bg-white hover:bg-gray-50">Load more</button>
                </div>
              </>
            )}
          </>
        ) : (
          /* News tab */
          <>
            {loadingNews ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => <div key={i} className="animate-pulse bg-white rounded-2xl p-5 border border-gray-100 min-h-[160px]" />)}
              </div>
            ) : error ? (
              <div className="text-center text-red-600 py-12">{error}</div>
            ) : newsFiltered.length === 0 ? (
              <div className="text-center text-gray-500 py-12">No news items found.</div>
            ) : (
              <>
                {/* featured first item for better visual hierarchy */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-4">
                  {newsFiltered.slice(0,3).map((n, idx) => (
                    <article key={n.id} className={`bg-white border border-gray-100 rounded-2xl p-4 shadow-sm hover:shadow-md transition flex ${idx===0 ? "lg:col-span-2" : ""}`}>
                      <div className="flex gap-4 w-full">
                        <div className="w-28 h-20 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center border flex-shrink-0">
                          {n.image ? <img src={n.image} alt={n.title} className="object-cover w-full h-full" onError={(e)=>{ e.currentTarget.onerror=null; e.currentTarget.src=getFavicon(n.sourceUrl) || 'https://via.placeholder.com/120x80?text=IMG'; }} /> : <div className="text-sm font-medium text-gray-600">{(n.source||"S").slice(0,2).toUpperCase()}</div>}
                        </div>

                        <div className="flex-1 min-w-0">
                          <h4 className="text-base font-semibold text-gray-900 truncate">{n.title}</h4>
                          <p className="mt-2 text-sm text-gray-600" style={clampStyle}>{n.snippet}</p>

                          <div className="mt-3 flex items-center justify-between">
                            <div className="text-xs text-gray-500">
                              {n.date ? new Date(n.date).toLocaleString() : <span>—</span>} • {n.source}
                            </div>

                            <div className="flex items-center gap-2">
                              <a href={n.sourceUrl || `https://duckduckgo.com/?q=${encodeURIComponent(n.title)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 inline-flex items-center gap-1">
                                Read <ExternalLink size={12} />
                              </a>
                              <button onClick={()=>setDebugItem(n)} className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-50 inline-flex items-center gap-1"><Eye size={12}/> Raw</button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>

                {/* rest of news */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {newsFiltered.slice(3).map(n => (
                    <article key={n.id} className="bg-white border border-gray-100 rounded-2xl p-3 shadow-sm hover:shadow-md transition flex flex-col">
                      <div className="flex gap-3 items-start">
                        <div className="w-28 h-20 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center border flex-shrink-0">
                          {n.image ? <img src={n.image} alt={n.title} className="object-cover w-full h-full" onError={(e)=>{ e.currentTarget.onerror=null; e.currentTarget.src=getFavicon(n.sourceUrl) || 'https://via.placeholder.com/120x80?text=IMG'; }} /> : <div className="text-sm font-medium text-gray-600">{(n.source||"S").slice(0,2).toUpperCase()}</div>}
                        </div>

                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-semibold text-gray-900 truncate">{n.title}</h4>
                          <p className="mt-2 text-sm text-gray-600" style={clampStyle}>{n.snippet}</p>

                          <div className="mt-3 flex items-center justify-between">
                            <div className="text-xs text-gray-500">
                              {n.date ? new Date(n.date).toLocaleString() : <span>—</span>} • {n.source}
                            </div>

                            <div className="flex items-center gap-2">
                              <a href={n.sourceUrl || `https://duckduckgo.com/?q=${encodeURIComponent(n.title)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 inline-flex items-center gap-1">
                                Read <ExternalLink size={12} />
                              </a>
                              <button onClick={()=>setDebugItem(n)} className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-50 inline-flex items-center gap-1"><Eye size={12}/> Raw</button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>

                <div className="mt-6 text-center text-sm text-gray-500">News powered by IndianAPI. Click Read to open original article.</div>
              </>
            )}
          </>
        )}
      </section>

      <footer className="mt-10 text-center text-xs text-gray-500">
        Data sources: Perplexity (deals) and IndianAPI (news) via your backend proxy. Use server env vars to control availability.
      </footer>

      {/* debug modal */}
      {debugItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg max-w-3xl w-full p-6 shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Raw data</h3>
              <button className="text-sm text-gray-500" onClick={() => setDebugItem(null)}>Close</button>
            </div>
            <pre className="text-xs overflow-auto max-h-[60vh] bg-gray-50 p-3 rounded">{JSON.stringify(debugItem.raw ?? debugItem, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
