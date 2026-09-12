// src/components/LiveNews.jsx
import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { API_ORIGIN } from "../config";

const CACHE_KEY = "markets_news_cache_v3";
const CACHE_TTL = 30 * 60 * 1000; // 30 minutes
const AUTO_REFRESH_INTERVAL = 2 * 60 * 60 * 1000; // 2 hours

/* ---------- helpers ---------- */
function buildApiBase() {
  const origin =
    (API_ORIGIN || import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
  return origin ? `${origin}/api` : "/api";
}

async function safeFetchRaw(url, opts = {}) {
  // wrapper to fetch and return {res, text, ct}
  const res = await fetch(url, opts);
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  const text = await res.text().catch(() => "");
  return { res, text, ct };
}

/**
 * Fetch JSON from backend path (prefers proxy at /api/news).
 * If backend returns non-JSON (HTML), we throw a friendly error so caller can fallback.
 */
async function fetchJsonFromBackend(path, signal) {
  const base = buildApiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const { res, text, ct } = await safeFetchRaw(url, { signal, credentials: "omit" });

  if (!res.ok) {
    const snippet = text ? text.slice(0, 200).replace(/\s+/g, " ") : res.statusText;
    throw new Error(`${res.status} ${res.statusText} — ${snippet}`);
  }

  // If content-type looks JSON-ish, parse it
  if (ct.includes("application/json") || ct.includes("+json") || ct.includes("json")) {
    try {
      return JSON.parse(text);
    } catch (err) {
      // parsing failed — treat as invalid JSON
      throw new Error("Invalid JSON received from news proxy");
    }
  }

  // Not JSON — throw a specific error so caller can try fallback
  throw new Error("NON_JSON_RESPONSE");
}

/**
 * Direct IndianAPI fetch (requires API key in env).
 * Returns parsed JSON or throws.
 */
async function fetchDirectIndianApiNews(signal) {
  const key =
    (typeof process !== "undefined" && process.env && process.env.REACT_APP_INDIANAPI_KEY) ||
    (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_INDIANAPI_KEY) ||
    null;
  if (!key) throw new Error("NO_INDIANAPI_KEY");

  const url = "https://stock.indianapi.in/news";
  const { res, text, ct } = await safeFetchRaw(url, { signal, headers: { "X-Api-Key": key, Accept: "application/json" } });

  if (!res.ok) {
    const snippet = text ? text.slice(0, 200).replace(/\s+/g, " ") : res.statusText;
    throw new Error(`${res.status} ${res.statusText} — ${snippet}`);
  }

  // IndianAPI might sometimes return JSON with different content-type; try parse regardless
  try {
    return JSON.parse(text);
  } catch (err) {
    // If content-type indicates JSON but parse failed, throw
    if (ct.includes("json")) throw new Error("Invalid JSON from IndianAPI");
    // otherwise treat as non-json
    throw new Error("NON_JSON_DIRECT");
  }
}

/* ---------- Main Component ---------- */
export default function LiveNews({ max = 6, variant = 'light' }) {
  const [items, setItems] = useState(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return { loadedAt: 0, items: [] };
      return JSON.parse(cached);
    } catch {
      return { loadedAt: 0, items: [] };
    }
  });

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [usingFallbackCache, setUsingFallbackCache] = useState(false);
  const ctrlRef = useRef(null);
  const isDark = variant === 'dark';

  useEffect(() => {
    const now = Date.now();
    if (!items.loadedAt || now - items.loadedAt > CACHE_TTL) {
      loadNews();
    }
    const interval = setInterval(() => loadNews({ force: true }), AUTO_REFRESH_INTERVAL);

    return () => {
      clearInterval(interval);
      if (ctrlRef.current) ctrlRef.current.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadNews({ force = false } = {}) {
    if (loading) return;
    const now = Date.now();
    if (!force && items.loadedAt && now - items.loadedAt <= CACHE_TTL) return;

    setLoading(true);
    setErrorMsg(null);
    setUsingFallbackCache(false);
    ctrlRef.current = new AbortController();
    const { signal } = ctrlRef.current;

    try {
      // Primary: backend proxy
      let body = null;
      try {
        body = await fetchJsonFromBackend("/news", signal);
      } catch (e) {
        // If backend returned NON_JSON_RESPONSE, try direct IndianAPI if key present
        if (String(e.message) === "NON_JSON_RESPONSE") {
          try {
            body = await fetchDirectIndianApiNews(signal);
          } catch (directErr) {
            // If direct call failed (no key or non-json), fallback to cached data
            console.warn("[LiveNews] Direct fallback failed:", directErr);
            const cached = loadCached();
            if (cached && cached.items && cached.items.length) {
              setUsingFallbackCache(true);
              setItems(cached);
              setErrorMsg("News service temporarily unavailable — using cached headlines.");
              return;
            }
            // No cached data: surface a friendly error
            const msg = directErr.message === "NO_INDIANAPI_KEY"
              ? "News proxy returned HTML and no IndianAPI key configured (set REACT_APP_INDIANAPI_KEY or VITE_INDIANAPI_KEY)."
              : "News service temporarily unavailable — received HTML instead of data";
            throw new Error(msg);
          }
        } else {
          // Other backend failure (network, 5xx with snippet, etc.)
          // try direct IndianAPI before bailing out
          try {
            body = await fetchDirectIndianApiNews(signal);
          } catch (directErr) {
            // use cached if available
            const cached = loadCached();
            if (cached && cached.items && cached.items.length) {
              setUsingFallbackCache(true);
              setItems(cached);
              setErrorMsg("News service temporarily unavailable — using cached headlines.");
              return;
            }
            // otherwise throw the original backend error message
            throw e;
          }
        }
      }

      // Normalize possible shapes
      let newsItems = [];
      if (!body) newsItems = [];
      else if (Array.isArray(body)) newsItems = body;
      else if (Array.isArray(body.data)) newsItems = body.data;
      else if (Array.isArray(body.articles)) newsItems = body.articles;
      else if (Array.isArray(body.items)) newsItems = body.items;
      else if (Array.isArray(body.news)) newsItems = body.news;
      else {
        // try to find a probable array inside object
        const maybe = Object.values(body).find((v) => Array.isArray(v));
        newsItems = Array.isArray(maybe) ? maybe : [];
      }

      const normalized = newsItems
        .map((n) => normalizeNewsItem(n))
        .filter((n) => n && (n.title || n.headline))
        .slice(0, 50);

      const out = { loadedAt: Date.now(), items: normalized };
      setItems(out);
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(out));
      } catch {
        console.warn("Failed to cache news in localStorage");
      }
      setErrorMsg(null);
    } catch (err) {
      console.error("LiveNews fetch failed:", err);
      setErrorMsg(String(err?.message || err));
    } finally {
      setLoading(false);
      ctrlRef.current = null;
    }
  }

  function loadCached() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function normalizeNewsItem(it = {}) {
    // common fields across different providers
    if (!it) return null;
    const title = it.title || it.headline || it.head || it.name || null;
    const summary = it.summary || it.description || it.snippet || it.body || "";
    const url = it.url || it.link || it.webUrl || it.article_url || it.articleUrl || "#";
    const img = it.image || it.image_url || it.thumbnail || it.mediaUrl || it.media_url || "";
    const date = it.publishedAt || it.published_at || it.pubDate || it.pub_date || it.date || it.time || null;
    const source = (it.source && (it.source.name || it.source)) || it.provider || it.publisher || it.source_name || it.sourceName || it.domain || "";
    return { title, summary, url, img, date, source };
  }

  function renderItem(it, i) {
    const title = it.title || it.headline || "Untitled";
    const summary = it.summary || it.description || "";
    const url = it.url || "#";
    const img = it.img || "";
    const date = it.date ? new Date(it.date).toLocaleString() : null;
    const source = it.source || "Unknown";

    if (isDark) {
      return (
        <article
          key={i}
          className="group rounded-xl border border-white/10 bg-white/5 overflow-hidden hover:border-blue-500/30 transition-colors"
        >
          <a href={url} target="_blank" rel="noopener noreferrer" className="flex gap-4 p-4">
            <div className="w-24 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-slate-800">
              {img ? (
                <img
                  src={img}
                  alt=""
                  className="object-cover w-full h-full"
                  loading="lazy"
                  onError={(e) => {
                    e.target.style.display = "none";
                  }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-slate-500">
                  News
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors line-clamp-2">
                {title}
              </p>
              {summary ? (
                <p className="text-xs text-slate-400 mt-1.5 line-clamp-2">{summary}</p>
              ) : null}
              <p className="text-xs text-slate-500 mt-2">
                {source}
                {date ? ` · ${date}` : ""}
              </p>
            </div>
          </a>
        </article>
      );
    }

    return (
      <article
        key={i}
        className="flex gap-3 py-2 border-b last:border-b-0 hover:bg-slate-50 transition-colors"
      >
        <div className="w-20 h-14 flex-shrink-0 rounded overflow-hidden bg-slate-100">
          {img ? (
            // allow img to error silently
            <img src={img} alt={title} className="object-cover w-full h-full" loading="lazy" onError={(e) => { e.target.style.display = "none"; }} />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xs text-slate-400">
              No image
            </div>
          )}
        </div>
        <div className="flex-1">
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-slate-800 hover:underline"
          >
            {title}
          </a>
          {summary ? <div className="text-xs text-slate-500 mt-1 line-clamp-2">{summary}</div> : null}
          <div className="text-xs text-slate-400 mt-1">
            {source} {date ? `• ${date}` : ""}
          </div>
        </div>
      </article>
    );
  }

  const list = (items.items || []).slice(0, max);

  if (isDark) {
    return (
      <div>
        {errorMsg && (
          <div className="text-sm text-amber-400 mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
            {String(errorMsg).slice(0, 300)}
          </div>
        )}

        {usingFallbackCache && (
          <div className="text-sm text-slate-400 mb-4">Showing cached headlines.</div>
        )}

        {loading && (
          <div className="grid md:grid-cols-2 gap-4">
            {Array.from({ length: max }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-white/5 animate-pulse" />
            ))}
          </div>
        )}

        {!loading && list.length === 0 && !errorMsg && (
          <p className="text-slate-400 text-center py-8">No headlines available right now.</p>
        )}

        {!loading && list.length > 0 && (
          <div className="grid md:grid-cols-2 gap-4">{list.map(renderItem)}</div>
        )}

        <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
          <p className="text-xs text-slate-500">IndianAPI · auto-refresh every 2 hours</p>
          <button
            type="button"
            onClick={() => loadNews({ force: true })}
            className="text-xs px-3 py-1.5 rounded-lg border border-white/15 text-slate-300 hover:bg-white/10 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="bg-white shadow-sm rounded p-3 border">
      <div className="flex items-baseline justify-between mb-2">
        <div>
          <h3 className="text-lg font-semibold">Latest Market News</h3>
          <p className="text-xs text-slate-500">Powered by IndianAPI</p>
        </div>
        <button
          onClick={() => loadNews({ force: true })}
          className="text-xs px-2 py-1 rounded border bg-slate-50 hover:bg-slate-100"
        >
          Refresh
        </button>
      </div>

      {/* --- States / messages --- */}
      {errorMsg && (
        <div className="text-xs text-orange-700 mb-2">
          ⚠️ {String(errorMsg).replace(/</g, "&lt;").slice(0, 300)}
        </div>
      )}

      {usingFallbackCache && (
        <div className="text-xs text-slate-500 mb-2">Showing cached headlines — the live news service is temporarily unavailable.</div>
      )}

      {loading && <div className="text-sm text-slate-500">Loading latest headlines…</div>}
      {!loading && list.length === 0 && !errorMsg && (
        <div className="text-sm text-slate-500">No news available at this moment.</div>
      )}

      {/* --- List --- */}
      <div>{list.map(renderItem)}</div>

      <div className="text-xs text-slate-400 mt-2">
        Source: IndianAPI News Feed • Auto-refresh every 2 hours (cached 30 min)
      </div>
    </section>
  );
}

LiveNews.propTypes = { max: PropTypes.number, variant: PropTypes.oneOf(['light', 'dark']) };
