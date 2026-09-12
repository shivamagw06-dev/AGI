import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  ClipboardPaste,
  Database,
  FileSearch,
  Loader2,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabaseClient';
import { getIpoPlatform } from '@/lib/ipoApi';
import { generateUniqueSlug, htmlToExcerpt } from '@/lib/articleUtils';
import {
  buildIpoArticleHtml,
  buildIpoKeyData,
  comparePastedWithUpstox,
  matchPastedIpoToUpstox,
  parseIpoPaste,
} from '@/lib/ipoPasteParser';

const GROUPS = [
  ['active', 'Open'],
  ['upcoming', 'Upcoming'],
  ['closed', 'Closed'],
  ['listed', 'Listed'],
];

const SCORE_LABELS = {
  business_quality: 'Business quality',
  financial_quality: 'Financial quality',
  valuation: 'Valuation',
  governance: 'Governance',
  issue_structure: 'Issue structure',
  demand_quality: 'Demand quality',
};

function ipoKey(ipo = {}) {
  return String(ipo.ipoId || ipo.symbol || ipo.isin || ipo.name || '');
}

function normalize(value = '') {
  return String(value).toLowerCase().replace(/\b(ipo|limited|ltd|company)\b/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
}

function findCoverage(ipo, articles) {
  if (!ipo) return null;
  const id = ipoKey(ipo).toLowerCase();
  const symbol = String(ipo.symbol || '').toUpperCase();
  const name = normalize(ipo.name);
  return articles.find((article) => {
    const meta = article.equity_research || {};
    const facts = meta.ipo_facts || {};
    return String(facts.upstox_ipo_id || '').toLowerCase() === id
      || (symbol && String(meta.ticker || '').toUpperCase() === symbol)
      || (name && normalize(meta.company_name) === name);
  }) || null;
}

function formatMoney(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(number)}` : 'Pending';
}

function StatusPill({ children, tone = 'slate' }) {
  const tones = {
    slate: 'border-slate-200 bg-slate-50 text-slate-600',
    green: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    red: 'border-red-200 bg-red-50 text-red-700',
  };
  return <span className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${tones[tone]}`}>{children}</span>;
}

export default function IpoIntelligenceImport() {
  const { user } = useAuth();
  const [platform, setPlatform] = useState(null);
  const [articles, setArticles] = useState([]);
  const [selectedKey, setSelectedKey] = useState('');
  const [query, setQuery] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [preview, setPreview] = useState(null);
  const [stance, setStance] = useState('neutral');
  const [gmp, setGmp] = useState({ value: '', source: '', updated_at: '' });
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [ipoData, articleResult] = await Promise.all([
        getIpoPlatform(),
        supabase
          .from('articles')
          .select('id, title, slug, status, tags, cover_url, published_at, author_id, equity_research')
          .eq('article_type', 'equity_research'),
      ]);
      if (articleResult.error) throw articleResult.error;
      setPlatform(ipoData);
      setArticles(articleResult.data || []);
    } catch (loadError) {
      setError(loadError?.message || 'Unable to load the IPO workspace.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadData(); }, []);

  const groupedIpos = useMemo(() => GROUPS.map(([key, label]) => [
    key,
    label,
    (platform?.[key] || []).filter((ipo) => !query.trim() || `${ipo.name} ${ipo.symbol || ''}`.toLowerCase().includes(query.trim().toLowerCase())),
  ]), [platform, query]);
  const allIpos = useMemo(() => GROUPS.flatMap(([key]) => platform?.[key] || []), [platform]);
  const selectedIpo = useMemo(() => allIpos.find((ipo) => ipoKey(ipo) === selectedKey) || null, [allIpos, selectedKey]);
  const existingArticle = useMemo(() => findCoverage(selectedIpo, articles), [selectedIpo, articles]);

  useEffect(() => {
    setPreview(null);
    setSuccess(null);
    const meta = existingArticle?.equity_research || {};
    setStance(meta.stance || 'neutral');
    setGmp({
      value: meta.ipo_gmp?.value || '',
      source: meta.ipo_gmp?.source || '',
      updated_at: meta.ipo_gmp?.updated_at || '',
    });
  }, [selectedKey, existingArticle?.id]);

  const extract = async () => {
    if (!pasteText.trim()) {
      setError('Paste the full IPO information first.');
      return;
    }
    setWorking(true);
    setError('');
    setSuccess(null);
    try {
      const parsed = parseIpoPaste(pasteText, { sourceUrl, sourceName: 'Chittorgarh' });
      const automaticMatch = matchPastedIpoToUpstox(parsed, platform || {});
      const target = selectedIpo || automaticMatch;
      if (!target) throw new Error('Select the matching IPO from the Upstox list before continuing.');
      if (selectedIpo && automaticMatch && ipoKey(selectedIpo) !== ipoKey(automaticMatch)) {
        throw new Error(`The pasted company matches ${automaticMatch.name}, not the selected IPO ${selectedIpo.name}. Choose the correct IPO before applying.`);
      }
      if (!selectedIpo) setSelectedKey(ipoKey(target));
      const conflicts = comparePastedWithUpstox(parsed, target);
      setPreview({ parsed, target, conflicts });
    } catch (extractError) {
      setPreview(null);
      setError(extractError?.message || 'The pasted information could not be structured.');
    } finally {
      setWorking(false);
    }
  };

  const publish = async () => {
    if (!preview?.parsed || !preview?.target) return;
    setWorking(true);
    setError('');
    setSuccess(null);
    try {
      const parsed = preview.parsed;
      const target = preview.target;
      const existing = findCoverage(target, articles);
      const previousMeta = existing?.equity_research || {};
      const ticker = String(target.symbol || target.ipoId || '').toUpperCase();
      const title = existing?.title || `${target.name || parsed.companyName} IPO Intelligence`;
      const html = buildIpoArticleHtml(parsed, target);
      const scoreEntries = Object.entries(parsed.suggestedScores).map(([key, suggested]) => [
        key,
        previousMeta.ipo_scores?.[key] !== '' && previousMeta.ipo_scores?.[key] != null
          ? previousMeta.ipo_scores[key]
          : suggested,
      ]);
      const tags = Array.from(new Set([
        ...(existing?.tags || []).filter((tag) => !String(tag).startsWith('homepage:')),
        'IPO',
        'equity-research',
        ticker,
        target.ipoId,
      ].filter(Boolean)));
      const now = new Date().toISOString();
      const equityResearch = {
        ...previousMeta,
        company_name: target.name || parsed.companyName,
        ticker,
        exchange: target.listingExchange || parsed.issue.listingAt || 'NSE',
        stance,
        report_date: now.slice(0, 10),
        report_label: 'IPO Research',
        currency: 'INR',
        key_data: buildIpoKeyData(parsed, target),
        thesis: parsed.thesis,
        strengths: parsed.strengths.join('\n'),
        risks: parsed.risks.join('\n'),
        ipo_gmp: {
          value: gmp.value,
          source: gmp.source,
          updated_at: gmp.updated_at,
        },
        ipo_scores: Object.fromEntries(scoreEntries),
        ipo_facts: {
          ...parsed,
          upstox_ipo_id: target.ipoId || null,
          upstox_symbol: target.symbol || null,
          upstox_status: target.status || null,
          upstox_matched_at: now,
          conflicts: preview.conflicts,
        },
      };
      const slug = existing?.slug || await generateUniqueSlug(title);
      const payload = {
        title,
        slug,
        section: 'IPOs',
        excerpt: htmlToExcerpt(parsed.thesis, 320),
        meta_description: htmlToExcerpt(parsed.thesis, 160),
        content_md: html,
        content: html,
        cover_url: existing?.cover_url || null,
        tags,
        status: 'published',
        article_type: 'equity_research',
        equity_research: equityResearch,
        published_at: existing?.published_at || now,
      };
      const result = existing
        ? await supabase.from('articles').update(payload).eq('id', existing.id).select('id, slug, status, title, tags, cover_url, published_at, author_id, equity_research').single()
        : await supabase.from('articles').insert({ ...payload, author_id: user.id }).select('id, slug, status, title, tags, cover_url, published_at, author_id, equity_research').single();
      if (result.error) throw result.error;
      setArticles((current) => [result.data, ...current.filter((article) => article.id !== result.data.id)]);
      setSuccess({
        mode: existing ? 'updated' : 'created',
        slug: result.data.slug,
        ipoPath: `/ipos/${encodeURIComponent(target.symbol || target.ipoId || '')}`,
      });
    } catch (saveError) {
      setError(saveError?.message || 'IPO intelligence could not be saved.');
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f1ea] text-[#102c3b]">
      <header className="border-b border-[#d9d5cc] bg-[#102c3b] text-white">
        <div className="mx-auto max-w-[1500px] px-5 py-9 lg:px-10">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#d3a273]">Content Studio / IPO desk</p>
              <h1 className="mt-3 font-serif text-3xl font-semibold sm:text-4xl">IPO intelligence input</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-white/60">Select a live Upstox issue, paste the source dossier, review the evidence, and update the public IPO page without placing it on the homepage.</p>
            </div>
            <button onClick={() => void loadData()} disabled={loading} className="inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2 text-xs font-bold text-white/80 hover:bg-white/10 disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh IPO list</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-5 py-8 lg:px-10">
        {error && <div className="mb-6 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div>}
        {success && <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4" />IPO intelligence {success.mode} and published.</span><div className="flex gap-4"><Link to={success.ipoPath} target="_blank" className="inline-flex items-center gap-1 font-bold">Open IPO page <ArrowUpRight className="h-4 w-4" /></Link><Link to={`/admin/articles/edit/${success.slug}`} className="font-bold">Full article editor</Link></div></div>}

        <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-[28px] border border-[#dcd8cf] bg-white p-5 shadow-[0_18px_60px_rgba(25,42,50,.06)]">
            <div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#9a6b46]">Step 1</p><h2 className="mt-1 font-serif text-xl font-semibold">Choose the issue</h2></div><Database className="h-5 w-5 text-[#9a6b46]" /></div>
            <label className="mt-5 flex items-center gap-2 rounded-xl border border-[#dfe3e3] bg-[#f7f7f4] px-3"><Search className="h-4 w-4 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company or symbol" className="w-full bg-transparent py-3 text-sm outline-none" /></label>
            <div className="mt-4 max-h-[560px] space-y-5 overflow-y-auto pr-1">
              {loading && <div className="flex items-center gap-2 py-10 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading Upstox IPOs</div>}
              {!loading && groupedIpos.map(([key, label, records]) => records.length ? <section key={key}><p className="mb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{label} · {records.length}</p><div className="space-y-2">{records.map((ipo) => { const selected = ipoKey(ipo) === selectedKey; const coverage = findCoverage(ipo, articles); return <button key={ipoKey(ipo)} onClick={() => setSelectedKey(ipoKey(ipo))} className={`w-full rounded-2xl border p-3 text-left transition ${selected ? 'border-[#173f53] bg-[#173f53] text-white' : 'border-[#e2e5e4] bg-white hover:border-[#c99a72]'}`}><div className="flex items-start justify-between gap-3"><span className="text-sm font-bold leading-5">{ipo.name}</span>{coverage && <CheckCircle2 className={`h-4 w-4 shrink-0 ${selected ? 'text-[#e6b98e]' : 'text-emerald-600'}`} />}</div><p className={`mt-2 text-[10px] uppercase tracking-[0.1em] ${selected ? 'text-white/55' : 'text-slate-400'}`}>{ipo.symbol || ipo.ipoId || label}{coverage ? ` · ${coverage.status}` : ' · no coverage'}</p></button>; })}</div></section> : null)}
            </div>
          </aside>

          <div className="space-y-6">
            <section className="rounded-[28px] border border-[#dcd8cf] bg-white p-6 shadow-[0_18px_60px_rgba(25,42,50,.06)] lg:p-8">
              <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#9a6b46]">Step 2</p><h2 className="mt-1 font-serif text-2xl font-semibold">Paste source dossier</h2></div>{selectedIpo && <StatusPill tone={existingArticle ? 'green' : 'amber'}>{existingArticle ? 'Existing coverage will update' : 'New coverage'}</StatusPill>}</div>
              {selectedIpo ? <div className="mt-5 grid gap-3 rounded-2xl bg-[#edf2f2] p-4 sm:grid-cols-4"><div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Selected IPO</p><p className="mt-1 text-sm font-bold">{selectedIpo.name}</p></div><div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Status</p><p className="mt-1 text-sm font-bold">{selectedIpo.status || 'Pending'}</p></div><div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Price band</p><p className="mt-1 text-sm font-bold">{formatMoney(selectedIpo.minPrice)} to {formatMoney(selectedIpo.maxPrice)}</p></div><div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Current article</p><p className="mt-1 text-sm font-bold">{existingArticle ? existingArticle.status : 'None'}</p></div></div> : <div className="mt-5 rounded-2xl border border-dashed border-[#d4cec3] p-5 text-sm text-slate-500">Choose an IPO from the left. If you paste first, the importer can suggest a matching issue.</div>}
              <label className="mt-5 block text-xs font-bold uppercase tracking-[0.1em] text-slate-500">Source URL<input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://www.chittorgarh.com/ipo/..." className="mt-2 w-full rounded-xl border border-[#dfe3e3] px-4 py-3 text-sm font-normal normal-case tracking-normal outline-none focus:border-[#9a6b46]" /></label>
              <label className="mt-4 block text-xs font-bold uppercase tracking-[0.1em] text-slate-500">Full IPO information<textarea value={pasteText} onChange={(event) => setPasteText(event.target.value)} placeholder="Paste the complete IPO page text here" className="mt-2 min-h-[300px] w-full resize-y rounded-2xl border border-[#dfe3e3] px-4 py-4 font-mono text-xs font-normal normal-case leading-6 tracking-normal outline-none focus:border-[#9a6b46]" /></label>
              <button onClick={() => void extract()} disabled={working || !pasteText.trim()} className="mt-5 inline-flex items-center gap-2 rounded-full bg-[#173f53] px-5 py-3 text-xs font-bold text-white hover:bg-[#0f3041] disabled:opacity-40">{working ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />} Extract and validate</button>
            </section>

            {preview && <section className="rounded-[28px] border border-[#dcd8cf] bg-white p-6 shadow-[0_18px_60px_rgba(25,42,50,.06)] lg:p-8">
              <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#9a6b46]">Step 3</p><h2 className="mt-1 font-serif text-2xl font-semibold">Review and apply</h2></div><StatusPill tone={preview.conflicts.length ? 'red' : 'green'}>{preview.conflicts.length ? `${preview.conflicts.length} provider conflicts` : `${preview.parsed.completeness}% complete`}</StatusPill></div>
              <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[
                ['Company', preview.parsed.companyName],
                ['Issue size', `${formatMoney(preview.parsed.issue.issueSizeCr)} crore`],
                ['Retail minimum', formatMoney(preview.parsed.application.retailAmount)],
                ['Subscription', preview.parsed.subscription.state === 'not_open' ? 'Not open yet' : preview.parsed.subscription.total != null ? `${preview.parsed.subscription.total}x` : 'Awaiting live data'],
              ].map(([label, value]) => <div key={label} className="rounded-2xl border border-[#e1e5e4] p-4"><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p><p className="mt-2 text-sm font-bold">{value}</p></div>)}</div>

              {preview.conflicts.length > 0 && <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4"><p className="flex items-center gap-2 text-sm font-bold text-red-800"><AlertTriangle className="h-4 w-4" />Pasted values differ from Upstox</p><ul className="mt-3 space-y-1 text-xs text-red-700">{preview.conflicts.map((item) => <li key={item.label}>{item.label}: pasted {item.pasted} / Upstox {item.upstox}</li>)}</ul></div>}
              {preview.parsed.warnings?.length > 0 && <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4"><p className="text-sm font-bold text-amber-800">Validation notes</p><ul className="mt-2 space-y-1 text-xs leading-5 text-amber-700">{preview.parsed.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}

              <div className="mt-6 grid gap-6 lg:grid-cols-2">
                <div><h3 className="text-xs font-bold uppercase tracking-[0.12em] text-emerald-700">Potential strengths</h3><ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">{preview.parsed.strengths.map((item) => <li key={item} className="flex gap-2"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />{item}</li>)}</ul></div>
                <div><h3 className="text-xs font-bold uppercase tracking-[0.12em] text-red-700">Principal risks</h3><ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">{preview.parsed.risks.map((item) => <li key={item} className="flex gap-2"><AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-red-500" />{item}</li>)}</ul></div>
              </div>

              <div className="mt-7 grid gap-4 rounded-2xl bg-[#f4f1ea] p-5 sm:grid-cols-2 lg:grid-cols-4">
                <label className="text-xs font-bold text-slate-600">Analyst stance<select value={stance} onChange={(event) => setStance(event.target.value)} className="mt-2 w-full rounded-xl border border-[#d7d5ce] bg-white px-3 py-2.5 text-sm"><option value="bullish">Bullish</option><option value="neutral">Neutral</option><option value="bearish">Bearish</option></select></label>
                <label className="text-xs font-bold text-slate-600">Manual GMP per share<input value={gmp.value} onChange={(event) => setGmp((current) => ({ ...current, value: event.target.value }))} inputMode="decimal" placeholder="Optional" className="mt-2 w-full rounded-xl border border-[#d7d5ce] bg-white px-3 py-2.5 text-sm" /></label>
                <label className="text-xs font-bold text-slate-600">GMP source<input value={gmp.source} onChange={(event) => setGmp((current) => ({ ...current, source: event.target.value }))} placeholder="IPO Guru" className="mt-2 w-full rounded-xl border border-[#d7d5ce] bg-white px-3 py-2.5 text-sm" /></label>
                <label className="text-xs font-bold text-slate-600">GMP observed at<input type="datetime-local" value={gmp.updated_at} onChange={(event) => setGmp((current) => ({ ...current, updated_at: event.target.value }))} className="mt-2 w-full rounded-xl border border-[#d7d5ce] bg-white px-3 py-2.5 text-sm" /></label>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-3">{Object.entries(SCORE_LABELS).map(([key, label]) => <div key={key} className="rounded-xl border border-[#e1e5e4] px-4 py-3"><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p><p className="mt-1 text-lg font-bold">{preview.parsed.suggestedScores[key] === '' ? 'Withheld' : preview.parsed.suggestedScores[key]}</p></div>)}</div>

              <div className="mt-7 flex flex-wrap items-center justify-between gap-4 border-t border-[#e4e2dc] pt-6"><div className="flex items-start gap-2 text-xs leading-5 text-slate-500"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#9a6b46]" /><span>Publishes to the selected IPO dossier. It does not add homepage tags or send subscriber email.</span></div><button onClick={() => void publish()} disabled={working} className="inline-flex items-center gap-2 rounded-full bg-[#9a6b46] px-6 py-3 text-xs font-bold text-white hover:bg-[#815637] disabled:opacity-40">{working ? <Loader2 className="h-4 w-4 animate-spin" /> : existingArticle ? <Save className="h-4 w-4" /> : <ClipboardPaste className="h-4 w-4" />}{existingArticle ? 'Update IPO intelligence' : 'Publish to IPO intelligence'}</button></div>
            </section>}
          </div>
        </div>
      </main>
    </div>
  );
}
