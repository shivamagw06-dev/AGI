import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight, BarChart3, Bell, Bookmark, BookmarkCheck, CalendarDays,
  Check, ChevronRight, Clock3, FileText, Info, Search, ShieldCheck,
  Sparkles, X,
} from 'lucide-react';
import useIpoPlatform from '@/hooks/useIpoPlatform';
import { matchArticlesToIpo } from '@/lib/ipoIntelligence';

const STATUS_TABS = [
  { id: 'open', label: 'Open now' },
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'closed', label: 'Closed' },
  { id: 'listed', label: 'Recently listed' },
];

const STATUS_META = {
  open: { label: 'Open', tone: 'bg-[#dff5e8] text-[#176b45]', dot: 'bg-[#1f9d63]' },
  upcoming: { label: 'Upcoming', tone: 'bg-[#e8f0f7] text-[#214f78]', dot: 'bg-[#3478a8]' },
  closed: { label: 'Closed', tone: 'bg-[#f1ede5] text-[#6f6556]', dot: 'bg-[#9c8e78]' },
  listed: { label: 'Listed', tone: 'bg-[#e9edf2] text-[#344054]', dot: 'bg-[#667085]' },
};

function parseDate(value) {
  if (!value) return null;
  const date = String(value).length > 10 ? new Date(value) : new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value, short = false) {
  const date = parseDate(value);
  if (!date) return 'To be announced';
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: short ? undefined : 'numeric' });
}

function formatNumber(value, fallback = 'Not disclosed') {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(number);
}

function priceBand(ipo) {
  if (ipo?.minPrice == null && ipo?.maxPrice == null) return 'Price pending';
  if (Number(ipo.minPrice) === Number(ipo.maxPrice)) return `₹${formatNumber(ipo.maxPrice)}`;
  return `₹${formatNumber(ipo.minPrice)} – ₹${formatNumber(ipo.maxPrice)}`;
}

function minimumInvestment(ipo) {
  const quantity = Number(ipo?.minimumBidQuantity || ipo?.lotSize);
  const price = Number(ipo?.maxPrice);
  return Number.isFinite(quantity) && Number.isFinite(price) ? quantity * price : null;
}

function daysUntil(value) {
  const target = parseDate(value);
  if (!target) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / 86400000);
}

function lifecycle(ipo, group) {
  const raw = String(ipo?.status || group || '').toLowerCase();
  if (raw.includes('list')) return 'listed';
  if (raw.includes('close')) return 'closed';
  if (raw.includes('upcoming')) return 'upcoming';
  return group === 'active' ? 'open' : group;
}

function grouped(items, group) {
  return (items || []).map((ipo) => ({ ...ipo, lifecycle: lifecycle(ipo, group) }));
}

function EmptyState({ filtered }) {
  return (
    <div className="col-span-full rounded-[24px] border border-dashed border-[#cbd2d9] bg-white px-6 py-14 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#edf3f5] text-[#173a4d]"><Search className="h-5 w-5" /></div>
      <h3 className="mt-4 font-serif text-xl font-semibold text-[#132a38]">{filtered ? 'No IPOs match these filters' : 'No IPOs in this stage'}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#66737d]">
        {filtered ? 'Try another company name or switch between Mainboard and SME.' : 'This view will update automatically when a new issue enters this stage.'}
      </p>
    </div>
  );
}

function IpoCard({ ipo, saved, compared, onSave, onCompare, researchArticles }) {
  const meta = STATUS_META[ipo.lifecycle] || STATUS_META.upcoming;
  const investment = minimumInvestment(ipo);
  const subscription = Number(ipo.subscriptionRate);
  const gmpValue = Number(ipo.gmp?.value);
  const hasGmp = Number.isFinite(gmpValue);
  const issuePrice = Number(ipo.cutOffPrice || ipo.maxPrice);
  const gmpPercentage = Number.isFinite(Number(ipo.gmp?.percentage))
    ? Number(ipo.gmp.percentage)
    : hasGmp && Number.isFinite(issuePrice) && issuePrice > 0 ? (gmpValue / issuePrice) * 100 : null;
  const closeIn = daysUntil(ipo.biddingEndDate);
  const urgent = ipo.lifecycle === 'open' && closeIn != null && closeIn >= 0;
  const matchingResearch = matchArticlesToIpo(researchArticles, ipo);
  const stance = matchingResearch.find((article) => article.researchMeta?.stance)?.researchMeta?.stance || null;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="group overflow-hidden rounded-[24px] border border-[#dfe5e8] bg-white shadow-[0_12px_35px_rgba(25,48,61,0.06)] transition hover:-translate-y-1 hover:border-[#9a7250] hover:shadow-[0_18px_48px_rgba(25,48,61,0.11)]"
    >
      <div className="h-1 bg-gradient-to-r from-[#173a4d] via-[#b47d52] to-[#d5b694]" />
      <div className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${meta.tone}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />{meta.label}
              </span>
              <span className="rounded-full border border-[#dfe5e8] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-[#66737d]">{ipo.isSme ? 'SME' : 'Mainboard'}</span>
              {stance && <span className="rounded-full bg-[#f7eee5] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-[#8a5e3c]">AGI {stance}</span>}
            </div>
            <Link to={`/ipos/${encodeURIComponent(ipo.symbol)}`} className="mt-4 block">
              <h2 className="line-clamp-2 font-serif text-[22px] font-semibold leading-tight text-[#132a38] transition group-hover:text-[#8a5e3c]">{ipo.name}</h2>
              <p className="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-[#81909a]">{ipo.symbol}</p>
            </Link>
          </div>
          <button type="button" onClick={() => onSave(ipo.symbol)} aria-label={saved ? 'Remove from watchlist' : 'Save to watchlist'} className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition ${saved ? 'border-[#c79870] bg-[#f7eee5] text-[#8a5e3c]' : 'border-[#dfe5e8] text-[#66737d] hover:border-[#c79870] hover:text-[#8a5e3c]'}`}>
            {saved ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
          </button>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-x-5 gap-y-4 border-y border-[#edf0f1] py-5">
          {[
            ['Price band', priceBand(ipo)],
            ['Min. investment', investment ? `₹${formatNumber(investment)}` : 'Pending'],
            ['Lot size', ipo.lotSize ? `${formatNumber(ipo.lotSize)} shares` : 'Pending'],
            ['Closes / listed', formatDate(ipo.biddingEndDate || ipo.listingDate, true)],
          ].map(([label, value]) => (
            <div key={label}><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#89949b]">{label}</p><p className="mt-1.5 text-sm font-bold text-[#132a38]">{value}</p></div>
          ))}
        </div>

        <div className="mt-5">
          <div className="flex items-end justify-between gap-3">
            <div><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#89949b]">Total subscription</p><p className="mt-1 text-2xl font-semibold text-[#173a4d]">{Number.isFinite(subscription) ? `${formatNumber(subscription)}x` : 'Awaiting data'}</p></div>
            <div className="text-right"><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#89949b]">Unofficial GMP</p><p className={`mt-1 text-xl font-semibold ${hasGmp && gmpValue >= 0 ? 'text-[#27734d]' : hasGmp ? 'text-[#a33e28]' : 'text-[#7b878e]'}`}>{hasGmp ? `${gmpValue >= 0 ? '+' : ''}₹${formatNumber(gmpValue)}` : 'Pending'}</p>{gmpPercentage != null && <p className="text-[10px] font-bold text-[#9a6944]">{gmpPercentage >= 0 ? '+' : ''}{gmpPercentage.toFixed(1)}%</p>}</div>
          </div>
          {urgent && <span className="mt-3 inline-flex rounded-full bg-[#fff1e8] px-3 py-1.5 text-[11px] font-bold text-[#a64d18]">{closeIn === 0 ? 'Closes today' : `${closeIn} day${closeIn === 1 ? '' : 's'} left`}</span>}
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#e9edef]"><div className="h-full rounded-full bg-gradient-to-r from-[#2b6076] to-[#c58a59] transition-all duration-700" style={{ width: `${Number.isFinite(subscription) ? Math.max(4, Math.min(100, subscription * 10)) : 0}%` }} /></div>
        </div>

        <div className="mt-5 flex items-center gap-2">
          <button type="button" onClick={() => onCompare(ipo.symbol)} className={`flex-1 rounded-full border px-4 py-2.5 text-xs font-bold transition ${compared ? 'border-[#173a4d] bg-[#173a4d] text-white' : 'border-[#cfd8dc] text-[#173a4d] hover:bg-[#edf3f5]'}`}>
            {compared ? <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5" /> Added</span> : 'Add to compare'}
          </button>
          <Link to={`/ipos/${encodeURIComponent(ipo.symbol)}`} className="flex h-10 w-10 items-center justify-center rounded-full bg-[#b47d52] text-white transition hover:bg-[#97623d]" aria-label={`Open ${ipo.name} dossier`}><ArrowRight className="h-4 w-4" /></Link>
        </div>
      </div>
    </motion.article>
  );
}

function ComparePanel({ items, onRemove, onClear }) {
  if (!items.length) return null;
  const rows = [
    ['Price band', priceBand],
    ['Minimum investment', (ipo) => minimumInvestment(ipo) ? `₹${formatNumber(minimumInvestment(ipo))}` : 'Pending'],
    ['Lot size', (ipo) => ipo.lotSize ? formatNumber(ipo.lotSize) : 'Pending'],
    ['Subscription', (ipo) => ipo.subscriptionRate != null ? `${formatNumber(ipo.subscriptionRate)}x` : 'Awaiting data'],
    ['Unofficial GMP', (ipo) => Number.isFinite(Number(ipo.gmp?.value)) ? `${Number(ipo.gmp.value) >= 0 ? '+' : ''}₹${formatNumber(ipo.gmp.value)}` : 'Pending'],
    ['Close date', (ipo) => formatDate(ipo.biddingEndDate, true)],
  ];
  return (
    <motion.section initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-5xl overflow-hidden rounded-[24px] border border-white/20 bg-[#102b3b]/[0.98] text-white shadow-[0_24px_80px_rgba(8,24,34,0.35)] backdrop-blur-xl sm:inset-x-6 sm:bottom-6">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#d5b694]">IPO comparison</p><p className="mt-1 text-sm text-white/70">Compare up to three issues side by side</p></div>
        <button type="button" onClick={onClear} className="rounded-full border border-white/15 px-3 py-1.5 text-xs font-bold text-white/75 hover:bg-white/10">Clear</button>
      </div>
      <div className="max-h-[48vh] overflow-auto px-5 py-4">
        <div className="grid min-w-[620px] gap-px overflow-hidden rounded-xl bg-white/10" style={{ gridTemplateColumns: `140px repeat(${items.length}, minmax(150px, 1fr))` }}>
          <div className="bg-[#102b3b] p-3" />
          {items.map((ipo) => <div key={ipo.symbol} className="relative bg-[#102b3b] p-3 pr-8"><p className="font-serif text-base font-semibold">{ipo.name}</p><p className="mt-1 text-[10px] font-bold tracking-[0.14em] text-white/50">{ipo.symbol}</p><button type="button" onClick={() => onRemove(ipo.symbol)} className="absolute right-2 top-2 text-white/50 hover:text-white" aria-label="Remove comparison"><X className="h-4 w-4" /></button></div>)}
          {rows.map(([label, render]) => <div key={label} className="contents"><div className="bg-white/[0.06] p-3 text-[10px] font-bold uppercase tracking-[0.12em] text-white/50">{label}</div>{items.map((ipo) => <div key={`${label}-${ipo.symbol}`} className="bg-white/[0.06] p-3 text-sm font-semibold">{render(ipo)}</div>)}</div>)}
        </div>
      </div>
    </motion.section>
  );
}

export default function IpoIntelligencePage() {
  const { loading, platform, error, research } = useIpoPlatform();
  const [status, setStatus] = useState('open');
  const [market, setMarket] = useState('all');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('closing');
  const [saved, setSaved] = useState(() => {
    try { return JSON.parse(localStorage.getItem('agi-ipo-watchlist') || '[]'); } catch { return []; }
  });
  const [compare, setCompare] = useState([]);

  useEffect(() => { localStorage.setItem('agi-ipo-watchlist', JSON.stringify(saved)); }, [saved]);

  const allIpos = useMemo(() => [
    ...grouped(platform?.active, 'active'), ...grouped(platform?.upcoming, 'upcoming'),
    ...grouped(platform?.closed, 'closed'), ...grouped(platform?.listed, 'listed'),
  ], [platform]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return allIpos
      .filter((ipo) => ipo.lifecycle === status)
      .filter((ipo) => market === 'all' || (market === 'sme' ? ipo.isSme : !ipo.isSme))
      .filter((ipo) => !needle || `${ipo.name} ${ipo.symbol}`.toLowerCase().includes(needle))
      .sort((a, b) => {
        if (sort === 'subscription') return Number(b.subscriptionRate || 0) - Number(a.subscriptionRate || 0);
        if (sort === 'investment') return Number(minimumInvestment(a) || Infinity) - Number(minimumInvestment(b) || Infinity);
        return (parseDate(a.biddingEndDate)?.getTime() || Infinity) - (parseDate(b.biddingEndDate)?.getTime() || Infinity);
      });
  }, [allIpos, status, market, query, sort]);

  const counts = {
    open: platform?.counts?.active ?? platform?.active?.length ?? 0,
    upcoming: platform?.counts?.upcoming ?? platform?.upcoming?.length ?? 0,
    closed: platform?.counts?.closed ?? platform?.closed?.length ?? 0,
    listed: platform?.counts?.listed ?? platform?.listed?.length ?? 0,
  };
  const compareItems = compare.map((symbol) => allIpos.find((ipo) => ipo.symbol === symbol)).filter(Boolean);
  const calendar = (platform?.calendar || []).filter((event) => parseDate(event.date)).slice(0, 7);
  const topResearch = research?.articles?.slice(0, 3) || [];
  const toggleSaved = (symbol) => setSaved((current) => current.includes(symbol) ? current.filter((item) => item !== symbol) : [...current, symbol]);
  const toggleCompare = (symbol) => setCompare((current) => current.includes(symbol) ? current.filter((item) => item !== symbol) : current.length >= 3 ? [...current.slice(1), symbol] : [...current, symbol]);

  return (
    <div className="min-h-screen bg-[#f5f3ee] text-[#132a38]">
      <Helmet><title>IPO Intelligence | Agarwal Global Investments</title><meta name="description" content="Track Indian IPOs, compare issue terms, monitor subscription and read independent AGI research." /></Helmet>

      <section className="relative overflow-hidden bg-[#102b3b] text-white">
        <div className="absolute inset-0 opacity-50" style={{ backgroundImage: 'radial-gradient(circle at 78% 20%, rgba(197,138,89,.28), transparent 28%), radial-gradient(circle at 10% 90%, rgba(72,133,155,.25), transparent 34%)' }} />
        <div className="absolute -right-24 top-10 hidden h-72 w-72 rounded-full border border-white/10 lg:block" />
        <div className="relative mx-auto grid max-w-[1500px] gap-10 px-4 py-12 sm:px-6 sm:py-16 lg:grid-cols-[1.35fr_.65fr] lg:px-8 lg:py-20">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[#d5b694]"><Sparkles className="h-4 w-4" /> AGI Primary Markets Desk</div>
            <h1 className="mt-6 max-w-4xl font-serif text-4xl font-semibold leading-[1.06] tracking-[-0.03em] sm:text-5xl lg:text-7xl">IPO decisions, with the noise removed.</h1>
            <p className="mt-6 max-w-2xl text-sm leading-7 text-[#c9d7dd] sm:text-base">Follow the full Indian IPO pipeline, compare issue terms and move from headline demand to disciplined, evidence-led research.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button type="button" onClick={() => setStatus('open')} className="rounded-full bg-[#c58a59] px-5 py-3 text-xs font-bold text-white transition hover:bg-[#d49b6d]">Explore open IPOs</button>
              <button type="button" onClick={() => document.getElementById('ipo-research')?.scrollIntoView({ behavior: 'smooth' })} className="rounded-full border border-white/20 px-5 py-3 text-xs font-bold text-white transition hover:bg-white/10">Read AGI research</button>
            </div>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.55, delay: 0.12 }} className="self-end rounded-[28px] border border-white/10 bg-white/[0.07] p-5 backdrop-blur sm:p-6">
            <div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/50">Primary market pulse</p><p className="mt-2 font-serif text-2xl font-semibold">Live pipeline</p></div><div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#c58a59]/20 text-[#e3b892]"><BarChart3 className="h-5 w-5" /></div></div>
            <div className="mt-6 grid grid-cols-3 gap-3">{[['Open', counts.open], ['Upcoming', counts.upcoming], ['Listed', counts.listed]].map(([label, value]) => <div key={label}><p className="text-2xl font-semibold">{value}</p><p className="mt-1 text-[10px] uppercase tracking-wider text-white/50">{label}</p></div>)}</div>
            <div className="mt-6 flex items-center gap-2 border-t border-white/10 pt-4 text-xs text-white/60"><Clock3 className="h-3.5 w-3.5" />{platform?.updatedAt ? `Updated ${new Date(platform.updatedAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}` : 'Refreshing market data'}</div>
          </motion.div>
        </div>
      </section>

      <main className="mx-auto max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <section className="rounded-[26px] border border-[#dfe5e8] bg-white p-3 shadow-[0_12px_35px_rgba(25,48,61,0.05)] sm:p-4">
          <div className="flex gap-2 overflow-x-auto pb-3 lg:pb-0">
            {STATUS_TABS.map((item) => <button key={item.id} type="button" onClick={() => setStatus(item.id)} className={`shrink-0 rounded-full px-4 py-2.5 text-xs font-bold transition ${status === item.id ? 'bg-[#173a4d] text-white shadow-sm' : 'bg-[#f2f4f3] text-[#5d6c75] hover:bg-[#e8edef]'}`}>{item.label} <span className={`ml-1.5 ${status === item.id ? 'text-[#d5b694]' : 'text-[#9aa4aa]'}`}>{counts[item.id]}</span></button>)}
            <div className="hidden flex-1 lg:block" />
            <div className="hidden shrink-0 items-center gap-2 rounded-full border border-[#dfe5e8] px-4 py-2.5 text-xs font-bold text-[#5d6c75] sm:flex"><Bookmark className="h-3.5 w-3.5" /> Saved {saved.length}</div>
          </div>
          <div className="mt-3 grid gap-3 border-t border-[#edf0f1] pt-3 md:grid-cols-[1fr_auto_auto]">
            <label className="relative block"><Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#89949b]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company or symbol" className="h-11 w-full rounded-full border border-[#dfe5e8] bg-[#fafbfa] pl-11 pr-4 text-sm outline-none transition placeholder:text-[#9aa4aa] focus:border-[#b47d52] focus:bg-white" /></label>
            <div className="flex rounded-full bg-[#f2f4f3] p-1">{[['all', 'All'], ['mainboard', 'Mainboard'], ['sme', 'SME']].map(([id, label]) => <button key={id} type="button" onClick={() => setMarket(id)} className={`rounded-full px-4 py-2 text-xs font-bold transition ${market === id ? 'bg-white text-[#173a4d] shadow-sm' : 'text-[#66737d]'}`}>{label}</button>)}</div>
            <select value={sort} onChange={(event) => setSort(event.target.value)} className="h-11 rounded-full border border-[#dfe5e8] bg-white px-4 text-xs font-bold text-[#4e5d66] outline-none focus:border-[#b47d52]"><option value="closing">Closing soon</option><option value="subscription">Highest subscription</option><option value="investment">Lowest investment</option></select>
          </div>
        </section>

        {platform?.unavailable && <div className="mt-5 flex items-start gap-3 rounded-2xl border border-[#ead6b7] bg-[#fff9ed] px-4 py-3 text-sm text-[#805d27]"><Info className="mt-0.5 h-4 w-4 shrink-0" /> Live provider refresh is delayed. The latest available snapshot is being shown.</div>}

        <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_330px]">
          <section>
            <div className="mb-5 flex items-end justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#a06b43]">Indian primary markets</p><h2 className="mt-2 font-serif text-3xl font-semibold tracking-tight">{STATUS_TABS.find((item) => item.id === status)?.label}</h2></div><p className="text-xs font-semibold text-[#78858d]">{visible.length} issue{visible.length === 1 ? '' : 's'}</p></div>
            {loading ? <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-[430px] animate-pulse rounded-[24px] border border-[#dfe5e8] bg-white" />)}</div>
              : error && !platform ? <div className="rounded-[24px] border border-[#ead4ce] bg-white px-6 py-12 text-center"><p className="font-serif text-xl font-semibold">IPO data is temporarily unavailable</p><p className="mt-2 text-sm text-[#66737d]">Research coverage remains available below.</p></div>
              : <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">{visible.map((ipo) => <IpoCard key={`${ipo.lifecycle}-${ipo.symbol}`} ipo={ipo} saved={saved.includes(ipo.symbol)} compared={compare.includes(ipo.symbol)} onSave={toggleSaved} onCompare={toggleCompare} researchArticles={research?.articles || []} />)}{!visible.length && <EmptyState filtered={Boolean(query || market !== 'all')} />}</div>}
          </section>

          <aside className="space-y-5">
            <section className="rounded-[24px] bg-[#e8ece8] p-5 sm:p-6">
              <div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#748178]">IPO calendar</p><h2 className="mt-2 font-serif text-2xl font-semibold">What happens next</h2></div><CalendarDays className="h-5 w-5 text-[#8a5e3c]" /></div>
              <div className="mt-6 space-y-1">
                {calendar.map((event, index) => { const date = parseDate(event.date); return <Link key={`${event.symbol}-${event.date}-${index}`} to={`/ipos/${encodeURIComponent(event.symbol)}`} className="group flex gap-4 rounded-xl px-2 py-3 transition hover:bg-white/60"><div className="w-11 shrink-0 text-center"><p className="font-serif text-xl font-semibold text-[#173a4d]">{date?.getDate()}</p><p className="text-[9px] font-bold uppercase tracking-wider text-[#7b8780]">{date?.toLocaleDateString('en-IN', { month: 'short' })}</p></div><div className="min-w-0 border-l border-[#cbd3ce] pl-4"><p className="text-[10px] font-bold uppercase tracking-wider text-[#9a6944]">{event.label}</p><p className="mt-1 truncate text-sm font-semibold text-[#263f4b]">{event.name}</p></div></Link>; })}
                {!calendar.length && <p className="py-6 text-sm leading-6 text-[#66737d]">Dates will appear when the exchange calendar is available.</p>}
              </div>
            </section>
            <section className="rounded-[24px] border border-[#dfe5e8] bg-white p-5 sm:p-6"><div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#edf3f5] text-[#173a4d]"><ShieldCheck className="h-5 w-5" /></div><h2 className="mt-4 font-serif text-xl font-semibold">A disciplined IPO checklist</h2><div className="mt-4 space-y-3">{['Read the RHP and use of proceeds', 'Compare valuation with listed peers', 'Separate subscription heat from quality', 'Size exposure for post-listing volatility'].map((item) => <div key={item} className="flex items-start gap-2.5 text-sm leading-5 text-[#596972]"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#9a6944]" />{item}</div>)}</div></section>
            <section className="overflow-hidden rounded-[24px] bg-[#b47d52] p-6 text-white"><Bell className="h-5 w-5" /><h2 className="mt-4 font-serif text-2xl font-semibold">Build your shortlist</h2><p className="mt-2 text-sm leading-6 text-white/80">Save an IPO to keep a personal watchlist on this device.</p><p className="mt-5 text-3xl font-semibold">{saved.length}</p><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/65">Saved issues</p></section>
          </aside>
        </div>

        <section id="ipo-research" className="mt-16 border-t border-[#d8dedf] pt-10 sm:mt-20">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#a06b43]">Independent perspective</p><h2 className="mt-2 font-serif text-3xl font-semibold sm:text-4xl">AGI IPO research</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-[#66737d]">Evidence-led analysis of business quality, valuation, risks and the post-listing setup.</p></div><Link to="/research" className="inline-flex items-center gap-2 text-xs font-bold text-[#173a4d] hover:text-[#8a5e3c]">View research library <ArrowRight className="h-4 w-4" /></Link></div>
          <div className="mt-7 grid gap-5 lg:grid-cols-3">
            {topResearch.map((article, index) => <motion.article key={article.id} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: index * 0.08 }} className="rounded-[22px] border border-[#dfe5e8] bg-white p-5"><div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#9a6944]">IPO research</span><FileText className="h-4 w-4 text-[#89949b]" /></div><Link to={`/article/${article.slug}`}><h3 className="mt-5 line-clamp-3 font-serif text-xl font-semibold leading-snug hover:text-[#8a5e3c]">{article.title}</h3></Link><p className="mt-3 line-clamp-2 text-sm leading-6 text-[#66737d]">{article.excerpt || 'Read the complete AGI research note.'}</p><Link to={`/article/${article.slug}`} className="mt-5 inline-flex items-center gap-1.5 text-xs font-bold text-[#173a4d]">Read analysis <ChevronRight className="h-3.5 w-3.5" /></Link></motion.article>)}
            {!topResearch.length && <div className="col-span-full rounded-[22px] border border-dashed border-[#cbd2d9] bg-white p-8 text-center text-sm text-[#66737d]">Published CMS articles from the IPO desk will appear here automatically.</div>}
          </div>
        </section>

        <section className="mt-12 flex items-start gap-3 rounded-[20px] border border-[#dfd6c9] bg-[#eee8df] p-5 text-xs leading-6 text-[#645c51]"><Info className="mt-1 h-4 w-4 shrink-0" /><p>IPO information is provided for educational and informational purposes only. It is not an offer, solicitation or investment recommendation. Always verify issue terms in the RHP and on NSE, BSE or SEBI before acting.</p></section>
      </main>
      <ComparePanel items={compareItems} onRemove={toggleCompare} onClear={() => setCompare([])} />
    </div>
  );
}
