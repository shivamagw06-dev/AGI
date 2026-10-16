import React, { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import {
  Download,
  FileText,
  RefreshCw,
  UploadCloud,
  Search as SearchIcon
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { supabase } from "@/lib/supabaseClient";

/**
 * ResearchNotes component
 *
 * Tabs: Notes | Trending | Deals | News | WorldBank
 *
 * Only the admin (set via VITE_ADMIN_EMAIL) can upload reports.
 *
 * NOTE: This client-side check is a UI convenience. You MUST enforce authorization server-side
 * (for example, validate the user's JWT on your server before accepting inserts or file uploads).
 */

const PAGE_SIZE = 8;
const API_BASE = import.meta.env.VITE_API_URL || window?.API_URL || "";
const ADMIN_EMAIL = import.meta.env.VITE_ADMIN_EMAIL || ""; // set this in .env

export default function ResearchNotes() {
  const { toast } = useToast();

  const [tab, setTab] = useState("notes");

  // Notes
  const [notes, setNotes] = useState([]);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  // Deals / News / Trending
  const [deals, setDeals] = useState([]);
  const [news, setNews] = useState([]);
  const [trending, setTrending] = useState([]);
  const [trendingPage, setTrendingPage] = useState(0);
  const [trendingHasMore, setTrendingHasMore] = useState(true);

  // WorldBank
  const [wbItems, setWbItems] = useState([]);
  const [wbPage, setWbPage] = useState(0);
  const [wbHasMore, setWbHasMore] = useState(true);

  // Loading states
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [trendingLoading, setTrendingLoading] = useState(false);
  const [trendingLoadingMore, setTrendingLoadingMore] = useState(false);
  const [wbLoading, setWbLoading] = useState(false);
  const [wbLoadingMore, setWbLoadingMore] = useState(false);

  // Search / filters / upload
  const [query, setQuery] = useState("");
  const [tagFilter, setTagFilter] = useState("all");
  const [uploading, setUploading] = useState(false);
  const [fileInput, setFileInput] = useState(null);

  // Auth/admin
  const [isAdmin, setIsAdmin] = useState(false);
  const [userEmail, setUserEmail] = useState(null);

  const mounted = useRef(false);
  const titleRef = useRef();
  const descRef = useRef();
  const tagsRef = useRef();

  // Helper: normalize getPublicUrl across supabase-js versions
  const safeGetPublicUrl = (bucket, path) => {
    try {
      const res = supabase.storage.from(bucket).getPublicUrl(path);
      // v2: { data: { publicUrl }, error }
      return res?.data?.publicUrl ?? res?.publicURL ?? null;
    } catch (e) {
      console.error("safeGetPublicUrl error", e);
      return null;
    }
  };

  // -----------------------
  // Auth: detect user & admin
  // -----------------------
  const detectUserAndAdmin = useCallback(async () => {
    try {
      const resp = await supabase.auth.getUser();
      const user = resp?.data?.user ?? null;
      const email = user?.email ?? null;
      setUserEmail(email);
      if (email && ADMIN_EMAIL && email.toLowerCase() === ADMIN_EMAIL.toLowerCase()) {
        setIsAdmin(true);
      } else {
        setIsAdmin(false);
      }
    } catch (err) {
      console.error("auth.getUser error", err);
      setUserEmail(null);
      setIsAdmin(false);
    }
  }, []);

  // -----------------------
  // Fetch Notes (Supabase)
  // -----------------------
  const fetchNotes = useCallback(async ({ reset = false } = {}) => {
    try {
      if (!mounted.current) return;
      if (reset) {
        setPage(0);
        setHasMore(true);
        setNotes([]);
      }

      const nextPage = reset ? 0 : page;
      setLoading(nextPage === 0);
      setLoadingMore(nextPage > 0);

      let q = supabase
        .from("research_notes")
        .select(
          "id,title,summary,body,source_name,source_url,image_url,tags,published_at,file_path,created_at"
        )
        .order("published_at", { ascending: false })
        .range(nextPage * PAGE_SIZE, nextPage * PAGE_SIZE + PAGE_SIZE - 1);

      if (query && query.trim()) {
        const like = `%${query.trim()}%`;
        q = q.or(`title.ilike.${like},summary.ilike.${like},body.ilike.${like}`);
      }

      if (tagFilter && tagFilter !== "all") {
        q = q.contains("tags", [tagFilter]);
      }

      const { data, error } = await q;
      if (error) throw error;

      const normalized = (data || []).map((r) => {
        const publicUrl = r.file_path ? safeGetPublicUrl("research-files", r.file_path) : null;
        return {
          id: r.id,
          title: r.title,
          summary: r.summary,
          description: r.body || r.summary,
          source_name: r.source_name,
          source_url: r.source_url,
          image: r.image_url,
          tags: r.tags || [],
          published_at: r.published_at || r.created_at,
          file_url: publicUrl,
          raw: r,
        };
      });

      if (reset) setNotes(normalized);
      else setNotes((prev) => [...prev, ...normalized]);

      if (!normalized.length || normalized.length < PAGE_SIZE) setHasMore(false);
      else setHasMore(true);

      setPage(nextPage + 1);
    } catch (err) {
      console.error("fetchNotes error:", err);
      toast({ title: "Error", description: "Failed to load research notes. See console.", variant: "destructive" });
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, tagFilter, toast, page]);

  // -----------------------
  // Fetch Trending (Perplexity)
  // -----------------------
  const fetchTrending = useCallback(async ({ reset = false } = {}) => {
    try {
      if (!mounted.current) return;
      if (reset) {
        setTrending([]);
        setTrendingLoading(true);
        setTrendingHasMore(true);
        setTrendingLoadingMore(false);
        setTrendingPage(0);
      }

      const nextPage = reset ? 0 : trendingPage;
      if (nextPage === 0) setTrendingLoading(true);
      else setTrendingLoadingMore(true);

      const url = `${API_BASE}/api/perplexity/trending?limit=${PAGE_SIZE}&page=${nextPage}`;
      const res = await fetch(url);
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(t || res.statusText);
      }
      const json = await res.json();
      const items = Array.isArray(json.items) ? json.items : json.data ?? [];
      const normalized = (items || []).map((it, i) => ({
        id: it.id ?? it.perplexity_id ?? `tr-${nextPage}-${i}`,
        perplexity_id: it.perplexity_id ?? it.id ?? null,
        title: it.title ?? (it.summary ? (it.summary.slice(0, 120) + "...") : "Untitled"),
        summary: it.summary ?? it.excerpt ?? "",
        body: it.body ?? "",
        score: typeof it.score === "number" ? it.score : it.relevance ?? null,
        confidence: it.confidence ?? null,
        sources: it.sources ?? it.citations ?? [],
        published_at: it.published_at ?? it.fetched_at ?? null,
        url: it.url ?? (it.sources?.[0]?.url) ?? null,
        raw: it,
      }));

      setTrending((prev) => [...prev, ...normalized]);

      // pagination: use server's next_page or heuristic
      if (json.next_page != null) {
        setTrendingHasMore(Boolean(json.next_page));
        setTrendingPage(nextPage + 1);
      } else {
        if (!normalized.length || normalized.length < PAGE_SIZE) setTrendingHasMore(false);
        else setTrendingHasMore(true);
        setTrendingPage(nextPage + 1);
      }
    } catch (err) {
      console.error("fetchTrending error:", err);
      toast({ title: "Trending load failed", description: "Check server logs", variant: "destructive" });
      // don't clear trending array on error — keep previous results
    } finally {
      setTrendingLoading(false);
      setTrendingLoadingMore(false);
    }
  }, [API_BASE, trendingPage, toast]);

  // -----------------------
  // Fetch Deals
  // -----------------------
  const fetchDeals = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/perplexity/deals?region=global&limit=12`);
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(t || res.statusText);
      }
      const json = await res.json();
      const arr = Array.isArray(json) ? json : json.parsed ?? json.data ?? [];
      setDeals((arr || []).map((it, i) => ({
        id: it.id ?? `deal-${i}`,
        acquirer: it.acquirer ?? it.buyer ?? "—",
        target: it.target ?? it.company ?? "—",
        sector: it.sector,
        value: it.value,
        region: it.region,
        date: it.date,
        source: it.source,
        raw: it,
      })));
    } catch (err) {
      console.error("fetchDeals error:", err);
      toast({ title: "Deals load failed", description: "Check server logs", variant: "destructive" });
      setDeals([]);
    } finally {
      setLoading(false);
    }
  }, [API_BASE, toast]);

  // -----------------------
  // Fetch News (IndianAPI)
  // -----------------------
  const fetchNews = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/news`);
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(t || res.statusText);
      }
      const json = await res.json();
      let arr = Array.isArray(json) ? json : json.data ?? json.articles ?? [];
      arr = arr || [];
      setNews(arr.map((it, i) => ({
        id: it.id ?? `news-${i}`,
        title: it.title ?? it.headline ?? "Untitled",
        snippet: it.description ?? it.summary ?? it.snippet ?? "",
        image: it.image || it.thumbnail || null,
        source: it.source || (it.url ? new URL(it.url).hostname : "source"),
        sourceUrl: it.url || it.link,
        publishedAt: it.publishedAt || it.date,
        raw: it,
      })));
    } catch (err) {
      console.error("fetchNews error:", err);
      toast({ title: "News load failed", description: "Check server logs", variant: "destructive" });
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [API_BASE, toast]);

  // -----------------------
  // Fetch World Bank Documents (proxied)
  // -----------------------
  const fetchWorldBank = useCallback(async ({ reset = false, qterm = "" } = {}) => {
    try {
      if (!mounted.current) return;
      if (reset) {
        setWbItems([]); setWbPage(0); setWbHasMore(true);
      }
      const nextPage = reset ? 0 : wbPage;
      setWbLoading(nextPage === 0);
      setWbLoadingMore(nextPage > 0);

      const params = new URLSearchParams({
        qterm: qterm || query || "",
        rows: String(PAGE_SIZE),
        os: String(nextPage * PAGE_SIZE),
        fl: "pdfurl,url,docna,docdt,repnme,lang_exact"
      });
      const url = `${API_BASE}/api/worldbank/search?${params.toString()}`;
      const res = await fetch(url);
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(t || res.statusText);
      }
      const json = await res.json();
      const docs = Array.isArray(json.items) ? json.items : json.data ?? json.results ?? json.docs ?? [];
      const normalized = (docs || []).map((d, i) => {
        const pdfUrl = d.pdfurl ?? (d.fields?.pdfurl) ?? null;
        const docUrl = d.url ?? (d.fields?.url) ?? null;
        const title = d.docna ?? d.title ?? (d.fields?.docna) ?? (d.fields?.title) ?? "WorldBank Document";
        const publishedAt = d.docdt ?? d.createdate ?? (d.fields?.docdt) ?? null;
        const authors = d.repnme ?? (d.fields?.repnme) ?? null;
        const lang = d.lang_exact ?? (d.fields?.lang_exact) ?? null;
        const summary = d.summary ?? d.abstract ?? d.fields?.abstract ?? "";

        return {
          id: d.id ?? d._id ?? `${publishedAt || ""}-${i}`,
          title,
          summary,
          pdfUrl,
          docUrl,
          publishedAt,
          authors,
          lang,
          raw: d,
        };
      });

      if (reset) setWbItems(normalized);
      else setWbItems(prev => [...prev, ...normalized]);

      if (json.total != null && typeof json.total === "number") {
        const totalFetched = (nextPage + 1) * PAGE_SIZE;
        setWbHasMore(totalFetched < json.total);
      } else {
        if (!normalized.length || normalized.length < PAGE_SIZE) setWbHasMore(false);
        else setWbHasMore(true);
      }

      setWbPage(nextPage + 1);
    } catch (err) {
      console.error("fetchWorldBank error:", err);
      toast({ title: "World Bank load failed", description: "Check server logs or proxy", variant: "destructive" });
      setWbItems([]);
    } finally {
      setWbLoading(false);
      setWbLoadingMore(false);
    }
  }, [API_BASE, wbPage, query, toast]);

  // -----------------------
  // Initial load
  // -----------------------
  useEffect(() => {
    mounted.current = true;
    detectUserAndAdmin();
    fetchNotes({ reset: true });
    fetchNews();
    // don't auto-fetch deals/trending/wb to conserve quotas - load on tab open
    return () => { mounted.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // reload notes when filters/search change
  useEffect(() => {
    setPage(0);
    setHasMore(true);
    fetchNotes({ reset: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, tagFilter]);

  // when switching tabs, fetch relevant content on demand
  useEffect(() => {
    if (tab === "trending" && trending.length === 0) fetchTrending({ reset: true });
    if (tab === "deals" && deals.length === 0) fetchDeals();
    if (tab === "news" && news.length === 0) fetchNews();
    if (tab === "worldbank" && wbItems.length === 0) fetchWorldBank({ reset: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  // -----------------------
  // Upload handler (admin)
  // -----------------------
  const handleFileChange = (e) => {
    setFileInput(e.target.files?.[0] ?? null);
  };

  const handleUpload = async (e) => {
    e.preventDefault();

    // CLIENT-SIDE guard: only admin may upload via UI
    if (!isAdmin) {
      toast({ title: "Unauthorized", description: "Only the admin can upload reports.", variant: "destructive" });
      return;
    }

    if (!fileInput) {
      toast({ title: "No file", description: "Choose a file first", variant: "destructive" });
      return;
    }
    const title = titleRef.current?.value?.trim() ?? "";
    const description = descRef.current?.value?.trim() ?? "";
    const tags = (tagsRef.current?.value ?? "").split(",").map(s => s.trim()).filter(Boolean);
    if (!title) {
      toast({ title: "Title required", description: "Provide a title for the report", variant: "destructive" });
      return;
    }

    try {
      setUploading(true);
      const filePath = `reports/${Date.now()}_${fileInput.name}`;
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from("research-files")
        .upload(filePath, fileInput, { cacheControl: "3600", upsert: false });

      if (uploadError) {
        console.error("Supabase upload error:", uploadError);
        throw uploadError;
      }

      const payload = {
        title,
        summary: description?.slice(0, 600),
        body: description,
        source_type: "UPLOAD",
        source_name: "AGI",
        source_url: null,
        image_url: null,
        tags,
        published_at: new Date().toISOString(),
        file_path: filePath,
      };

      const { data: insertData, error: insertError } = await supabase.from("research_notes").insert([payload]).select();
      if (insertError) {
        console.error("insert error:", insertError);
        throw insertError;
      }

      toast({ title: "Uploaded", description: "Report uploaded and saved." });
      fetchNotes({ reset: true });
      if (e?.target && typeof e.target.reset === "function") e.target.reset();
      setFileInput(null);
    } catch (err) {
      console.error("upload failed", err);
      toast({ title: "Upload failed", description: err?.message || "See console", variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  // -----------------------
  // Downloads
  // -----------------------
  const handleDownload = (note) => {
    if (!note?.file_url) {
      toast({ title: "No file", description: "This note has no file to download.", variant: "destructive" });
      return;
    }
    window.open(note.file_url, "_blank", "noopener,noreferrer");
    toast({ title: "Opening file", description: note.title ?? "Report" });
  };

  // -----------------------
  // UI helpers: available tags from notes
  // -----------------------
  const availableTags = React.useMemo(() => {
    const s = new Set();
    notes.forEach(n => (n.tags || []).forEach(t => s.add(t)));
    return ["all", ...Array.from(s).slice(0, 30)];
  }, [notes]);

  // -----------------------
  // Render
  // -----------------------
  return (
    <section className="py-20 bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between gap-6 mb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-extrabold text-foreground">In-Depth Research</h1>
            <p className="mt-1 text-muted-foreground max-w-xl">
              Download deep-dive reports, browse trending research, World Bank documents, curated deals and the latest market news.
            </p>
            <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
              <span className="inline-flex items-center gap-2"><FileText className="w-4 h-4" /> Notes</span>
              <span>•</span>
              <span className="inline-flex items-center gap-2"><RefreshCw className="w-4 h-4" /> Updated live</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <select value={tab} onChange={e => setTab(e.target.value)} className="border px-3 py-2 rounded bg-white">
              <option value="notes">Notes</option>
              <option value="trending">Trending</option>
              <option value="deals">Deals</option>
              <option value="news">News</option>
              <option value="worldbank">World Bank</option>
            </select>

            <Button onClick={() => {
              if (tab === "notes") fetchNotes({ reset: true });
              else if (tab === "trending") fetchTrending({ reset: true });
              else if (tab === "deals") fetchDeals();
              else if (tab === "news") fetchNews();
              else if (tab === "worldbank") fetchWorldBank({ reset: true });
              toast({ title: "Refreshing", description: "Fetching latest content..." });
            }} className="inline-flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
          </div>
        </motion.div>

        {/* Search / filters */}
        <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={tab === "news" ? "Search news..." : "Search title, summary..."}
              className="pl-10 pr-3 py-2 border rounded w-full"
            />
          </div>

          {tab === "notes" && (
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600">Tag:</label>
              <select value={tagFilter} onChange={(e) => setTagFilter(e.target.value)} className="border px-3 py-2 rounded">
                {availableTags.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          )}
        </div>

        {/* CONTENT AREA */}
        <div>
          {/* NOTES */}
          {tab === "notes" && (
            <>
              {loading && notes.length === 0 ? (
                <div className="grid gap-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="animate-pulse bg-card border border-border rounded-lg p-6 flex items-center gap-6" />
                  ))}
                </div>
              ) : notes.length === 0 ? (
                <div className="bg-card border border-border rounded-lg p-6 text-center text-muted-foreground">
                  No research notes available yet. You can upload reports (admin).
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {notes.map((n) => (
                    <motion.article key={n.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-lg p-4 flex flex-col">
                      <div className="flex items-start gap-4">
                        <div className="w-20 h-20 rounded bg-gray-50 overflow-hidden flex items-center justify-center">
                          {n.image ? <img src={n.image} alt={n.title} className="object-cover w-full h-full" /> : <FileText className="w-8 h-8 text-gray-400" />}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-muted-foreground mb-1">{n.published_at ? new Date(n.published_at).toLocaleDateString() : "—"}</div>
                          <h3 className="text-lg font-semibold truncate">{n.title}</h3>
                          <p className="mt-2 text-sm text-gray-600 line-clamp-3">{n.summary || n.description}</p>

                          <div className="mt-3 flex items-center gap-2 flex-wrap">
                            {(n.tags || []).slice(0, 5).map(t => <span key={t} className="text-xs bg-gray-100 px-2 py-1 rounded-full">{t}</span>)}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-between">
                        <div className="text-sm text-gray-500">{n.source_name ?? (n.raw?.source_name) ?? ""}</div>
                        <div className="flex items-center gap-2">
                          <Button onClick={() => handleDownload(n)} className="inline-flex items-center gap-2">
                            <Download className="w-4 h-4" /> Download
                          </Button>
                          <a href={n.source_url || "#"} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">View source</a>
                        </div>
                      </div>
                    </motion.article>
                  ))}
                </div>
              )}

              {/* Load more */}
              <div className="mt-6 flex justify-center">
                {hasMore ? (
                  <Button onClick={() => fetchNotes({ reset: false })} className="px-4 py-2">
                    {loadingMore ? "Loading..." : "Load more"}
                  </Button>
                ) : (
                  <div className="text-sm text-gray-500">No more reports</div>
                )}
              </div>

              {/* Upload form (admin) */}
              <div className="mt-8 bg-card border border-border rounded-lg p-4">
                <h4 className="font-semibold mb-2">Upload new research (admin)</h4>

                {isAdmin ? (
                  <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                    <div className="md:col-span-2 flex flex-col gap-2">
                      <input ref={titleRef} placeholder="Title" className="border px-3 py-2 rounded" />
                      <input ref={descRef} placeholder="Short description / summary" className="border px-3 py-2 rounded" />
                      <input ref={tagsRef} placeholder="Tags (comma separated)" className="border px-3 py-2 rounded" />
                    </div>

                    <div className="flex items-center gap-2">
                      <input type="file" accept=".pdf,.md,.docx" onChange={handleFileChange} />
                      <Button type="submit" disabled={uploading} className="inline-flex items-center gap-2">
                        <UploadCloud className="w-4 h-4" /> {uploading ? "Uploading..." : "Upload"}
                      </Button>
                    </div>
                  </form>
                ) : (
                  <div className="text-sm text-gray-600">
                    Only the admin can upload reports. {userEmail ? `Signed in as ${userEmail}` : "You are not signed in."}
                  </div>
                )}
              </div>
            </>
          )}

          {/* TRENDING */}
          {tab === "trending" && (
            <>
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold">Trending research (Perplexity)</h3>
                <div className="text-sm text-gray-500">{trending.length} items</div>
              </div>

              {trendingLoading && trending.length === 0 ? (
                <div className="grid gap-4">
                  {Array.from({ length: 6 }).map((_, i) => <div key={i} className="animate-pulse bg-card border border-border rounded-lg p-6" />)}
                </div>
              ) : trending.length === 0 ? (
                <div className="bg-card border border-border rounded-lg p-6 text-center text-muted-foreground">No trending items found.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {trending.map(item => (
                    <article key={item.id} className="bg-card border border-border rounded-lg p-4 flex flex-col">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-3">
                            <h4 className="text-sm font-semibold truncate">{item.title}</h4>
                            <div className="text-xs text-gray-500 flex items-center gap-2">
                              <span className="px-2 py-1 rounded-full text-[10px] bg-yellow-50 border border-yellow-100">Perplexity</span>
                              {typeof item.score === "number" && <span className="text-xs font-medium">{(item.score * 100).toFixed(0)}%</span>}
                            </div>
                          </div>

                          <p className="mt-2 text-sm text-gray-600 line-clamp-4">{item.summary}</p>

                          <div className="mt-3 text-xs text-gray-500">
                            <div>
                              {item.published_at ? new Date(item.published_at).toLocaleString() : "—"}
                            </div>
                            {item.sources && item.sources.length > 0 && (
                              <div className="mt-1 truncate">Source: {(item.sources[0].domain || item.sources[0].url || "").replace(/^https?:\/\//, "")}</div>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <a href={item.url || `https://duckduckgo.com/?q=${encodeURIComponent(item.title)}`} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">View full</a>
                          <button onClick={() => toast({ title: "Feedback", description: "Thanks — feedback recorded (backend required)" })} className="text-sm text-green-600 hover:underline">Helpful</button>
                        </div>

                        <div className="text-xs text-gray-500">
                          <button onClick={() => toast({ title: "Raw", description: "Open console to view raw data" })} className="text-xs text-gray-400">Raw</button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}

              <div className="mt-6 flex justify-center">
                {trending.length > 0 && trendingHasMore && (
                  <Button onClick={() => fetchTrending({ reset: false })} className="px-4 py-2">
                    {trendingLoadingMore ? "Loading..." : "Load more"}
                  </Button>
                )}
              </div>
            </>
          )}

          {/* DEALS */}
          {tab === "deals" && (
            <>
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold">Latest deals</h3>
                <div className="text-sm text-gray-500">{deals.length} items</div>
              </div>

              {loading ? (
                <div className="grid gap-4">
                  {Array.from({ length: 6 }).map((_, i) => <div key={i} className="animate-pulse bg-card border border-border rounded-lg p-6" />)}
                </div>
              ) : deals.length === 0 ? (
                <div className="bg-card border border-border rounded-lg p-6 text-center text-muted-foreground">No deals found.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {deals.map(d => (
                    <article key={d.id} className="bg-card border border-border rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="text-sm text-gray-500">{d.date ? new Date(d.date).toLocaleDateString() : "—"}</div>
                          <h4 className="text-lg font-semibold">{d.acquirer} <span className="text-gray-400 mx-1">→</span> {d.target}</h4>
                          <div className="mt-2 text-sm text-gray-600">{d.sector} • {d.region}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-500">Value</div>
                          <div className="font-bold">{d.value ?? "Undisclosed"}</div>
                        </div>
                      </div>
                      <div className="mt-3 flex items-center justify-between">
                        <div className="text-sm text-gray-500">{d.source ? (new URL(d.source).hostname) : ""}</div>
                        {d.source ? <a className="text-sm text-blue-600" href={d.source} target="_blank" rel="noopener noreferrer">Read</a> : <span className="text-sm text-gray-400">No source</span>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}

          {/* NEWS */}
          {tab === "news" && (
            <>
              {loading ? (
                <div className="grid gap-4">
                  {Array.from({ length: 6 }).map((_, i) => <div key={i} className="animate-pulse bg-card border border-border rounded-lg p-6" />)}
                </div>
              ) : news.length === 0 ? (
                <div className="bg-card border border-border rounded-lg p-6 text-center text-muted-foreground">No news items found.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {news.map(n => (
                    <article key={n.id} className="bg-card border border-border rounded-lg p-3 flex flex-col">
                      <div className="flex gap-3">
                        <div className="w-28 h-20 rounded overflow-hidden bg-gray-50 flex items-center justify-center">
                          {n.image ? <img src={n.image} alt={n.title} className="object-cover w-full h-full" /> : <FileText className="w-6 h-6 text-gray-400" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-semibold truncate">{n.title}</h4>
                          <p className="mt-2 text-sm text-gray-600 line-clamp-3">{n.snippet}</p>
                          <div className="mt-3 flex items-center justify-between">
                            <div className="text-xs text-gray-500">{n.source} • {n.publishedAt ? new Date(n.publishedAt).toLocaleString() : "—"}</div>
                            <div className="flex items-center gap-2">
                              <a href={n.sourceUrl || `https://duckduckgo.com/?q=${encodeURIComponent(n.title)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600">Read</a>
                              <Button size="sm" variant="ghost" onClick={() => toast({ title: "Raw", description: "Open console to view raw data" })}>Raw</Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}

          {/* WORLD BANK */}
          {tab === "worldbank" && (
            <>
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold">World Bank Documents & Reports</h3>
                <div className="text-sm text-gray-500">{wbItems.length} items</div>
              </div>

              {wbLoading && wbItems.length === 0 ? (
                <div className="grid gap-4">
                  {Array.from({ length: 6 }).map((_, i) => <div key={i} className="animate-pulse bg-card border border-border rounded-lg p-6" />)}
                </div>
              ) : wbItems.length === 0 ? (
                <div className="bg-card border border-border rounded-lg p-6 text-center text-muted-foreground">No World Bank documents found.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {wbItems.map(doc => (
                    <article key={doc.id} className="bg-card border border-border rounded-lg p-4 flex flex-col">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-semibold truncate">{doc.title}</h4>
                          <p className="mt-2 text-sm text-gray-600 line-clamp-4">{doc.summary || "Summary not available."}</p>

                          <div className="mt-3 text-xs text-gray-500">
                            <div>{doc.publishedAt ? new Date(doc.publishedAt).toLocaleDateString() : "—"}</div>
                            {doc.authors && <div>Report: {doc.authors}</div>}
                            {doc.lang && <div>Lang: {doc.lang}</div>}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {doc.pdfUrl ? (
                            <a href={doc.pdfUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                              <Download className="inline w-4 h-4 mr-1" /> Download PDF
                            </a>
                          ) : doc.docUrl ? (
                            <a href={doc.docUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">View Document</a>
                          ) : (
                            <span className="text-sm text-gray-400">No file/link</span>
                          )}
                        </div>

                        <div className="text-xs text-gray-500">
                          <button onClick={() => toast({ title: "Raw", description: "Open console to view raw data" })} className="text-xs text-gray-400">Raw</button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}

              {/* Load more WB */}
              <div className="mt-6 flex justify-center">
                {wbHasMore ? (
                  <Button onClick={() => fetchWorldBank({ reset: false })} className="px-4 py-2">
                    {wbLoadingMore ? "Loading..." : "Load more"}
                  </Button>
                ) : (
                  <div className="text-sm text-gray-500">No more documents</div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="mt-12 text-center text-xs text-gray-500">
          Data sources: Supabase (notes), Perplexity (trending & deals, proxied), IndianAPI (news, proxied), World Bank Documents & Reports (proxied). Manage keys on server environment. Not investment advice.
        </div>
      </div>
    </section>
  );
}
